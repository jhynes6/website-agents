#!/usr/bin/env python3
"""
Migrate DigitalOcean Spaces objects into Pinecone.

Why this exists:
  Pinecone "bulk import" supports AWS S3 / GCS / Azure (see pinecone-object-import.md),
  but DigitalOcean Spaces is only S3-*compatible* and not an AWS S3 bucket. In practice,
  bulk-import-from-Spaces is not a safe assumption.

So this script implements the reliable path:
  Spaces -> download -> chunk text -> Pinecone upsert_records (integrated embedding)

This gives us:
  - Namespaces for multitenancy (namespace == client_slug)
  - Flat, filterable metadata fields on every chunk record (content_type, document_source, file_key, etc.)

Usage (repo root):
  backend/venv/bin/python backend/scripts/migrate_spaces_to_pinecone.py \
    --client-slug wendt-partners \
    --prefix wendt-partners/ \
    --limit-files 5
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
import sys
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Add backend dir for imports when run from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.config import get_settings  # noqa: E402
from app.clients.digital_ocean_client import do_client  # noqa: E402


YAML_FM_RE = re.compile(r"(?s)^---\n(.*?)\n---\n")
MD_CODEBLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
MD_IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]+\)")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MD_HTML_TAG_RE = re.compile(r"<[^>]+>")


def parse_yaml_frontmatter(text: str) -> Dict[str, str]:
    """
    Minimal YAML frontmatter parser for flat 'key: value' pairs.
    We intentionally keep this conservative: no nested YAML, no lists.
    """
    m = YAML_FM_RE.match(text)
    if not m:
        return {}
    block = m.group(1)
    out: Dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def strip_yaml_frontmatter(text: str) -> str:
    m = YAML_FM_RE.match(text)
    if not m:
        return text
    return text[m.end() :]

def clean_for_keywords(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    t = MD_CODEBLOCK_RE.sub(" ", t)
    t = MD_IMAGE_RE.sub(" ", t)
    t = MD_LINK_RE.sub(r"\1", t)
    t = MD_HTML_TAG_RE.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def stable_id(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="ignore"))
        h.update(b"\0")
    return h.hexdigest()[:32]


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Simple character-based chunking with overlap.
    Good enough for migration; we can swap for smarter chunking later.
    """
    text = text.strip()
    if not text:
        return []
    if chunk_size <= 0:
        return [text]
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 5)
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


@dataclass
class SpacesObject:
    key: str
    size: int


def list_spaces_objects(bucket: str, prefix: str, limit: Optional[int]) -> List[SpacesObject]:
    if not do_client.s3_client:
        raise RuntimeError("Spaces client not configured (DIGITALOCEAN_SPACES_KEY/SECRET)")
    out: List[SpacesObject] = []
    token: Optional[str] = None
    while True:
        kwargs: Dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = do_client.s3_client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []) or []:
            k = obj.get("Key")
            if not k:
                continue
            if k.endswith("/") or k.endswith("metadata.json"):
                # skip folder markers and old client metadata files
                continue
            out.append(SpacesObject(key=k, size=int(obj.get("Size") or 0)))
            if limit and len(out) >= limit:
                return out
        if not resp.get("IsTruncated"):
            return out
        token = resp.get("NextContinuationToken")


def get_spaces_object_text(bucket: str, key: str, max_bytes: int) -> Optional[str]:
    if not do_client.s3_client:
        raise RuntimeError("Spaces client not configured (DIGITALOCEAN_SPACES_KEY/SECRET)")
    # Only read the first max_bytes to keep this safe for "try it" runs.
    resp = do_client.s3_client.get_object(
        Bucket=bucket,
        Key=key,
        Range=f"bytes=0-{max_bytes-1}",
    )
    raw = resp["Body"].read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="ignore")


def looks_texty(key: str) -> bool:
    ext = key.lower().rsplit(".", 1)[-1] if "." in key else ""
    return ext in {"md", "txt", "html", "htm", "json", "jsonl", "xml", "csv", "tsv", "rst"}


def ensure_pinecone_index(
    api_key: str,
    index_name: str,
    cloud: str,
    region: str,
    text_field: str,
):
    """
    Create (or reuse) a Pinecone index configured for integrated embedding with a single text field.
    """
    from pinecone import Pinecone, CloudProvider, AwsRegion, IndexEmbed, EmbedModel

    pc = Pinecone(api_key=api_key)

    # Map cloud/region to SDK enums (keep conservative; extend as needed)
    cloud_norm = cloud.strip().lower()
    if cloud_norm != "aws":
        raise ValueError("This script currently supports only Pinecone serverless AWS indexes (cloud=aws).")

    # AwsRegion enum uses names like US_EAST_1; convert from "us-east-1"
    region_norm = region.strip().lower().replace("-", "_")
    aws_region = getattr(AwsRegion, region_norm.upper(), None)
    if aws_region is None:
        raise ValueError(f"Unsupported AWS region for Pinecone SDK enum: {region}")

    # If index exists, describe to get host
    try:
        desc = pc.describe_index(index_name)
        host = desc.host
        return pc, host
    except Exception:
        pass

    # Create index for model
    index_config = pc.create_index_for_model(
        name=index_name,
        cloud=CloudProvider.AWS,
        region=aws_region,
        # NOTE: Pinecone API currently rejects embed.metric=None (expects string), so pass a concrete metric.
        embed=IndexEmbed(
            model=EmbedModel.Multilingual_E5_Large,
            field_map={"text": text_field},
            metric="cosine",
        ),
    )
    return pc, index_config.host


def upsert_records_in_batches(index, namespace: str, records: List[Dict[str, Any]], batch_size: int = 100) -> int:
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        index.upsert_records(namespace=namespace, records=batch)
        total += len(batch)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate DO Spaces objects into Pinecone (upsert_records)")
    parser.add_argument("--client-slug", required=True, help="Client slug. Used as Pinecone namespace.")
    parser.add_argument("--prefix", required=True, help="Spaces prefix (folder), e.g. wendt-partners/website_docs/")
    parser.add_argument("--index-name", default=None, help="Pinecone index name (default from env PINECONE_KB_INDEX)")
    parser.add_argument("--cloud", default=None, help="Pinecone cloud (default from env PINECONE_CLOUD)")
    parser.add_argument("--region", default=None, help="Pinecone region (default from env PINECONE_REGION)")
    parser.add_argument("--limit-files", type=int, default=1, help="Max files to migrate (default 1 for safety)")
    parser.add_argument("--chunk-size", type=int, default=1200, help="Chunk size in characters")
    parser.add_argument("--overlap", type=int, default=200, help="Chunk overlap in characters")
    parser.add_argument("--max-bytes", type=int, default=200_000, help="Max bytes to read per file (default 200KB)")
    parser.add_argument("--text-field", default="text", help="Name of the text field in Pinecone record schema")
    parser.add_argument("--add-keywords", action="store_true", help="Generate 3-5 keywords per file via LLM (requires OPENAI_API_KEY)")
    parser.add_argument("--dry-run", action="store_true", help="Don’t upsert; just print what would happen")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.pinecone_api_key:
        raise SystemExit("PINECONE_API_KEY not configured in backend/.env")
    if not settings.digitalocean_spaces_bucket:
        raise SystemExit("DIGITALOCEAN_SPACES_BUCKET not configured")

    index_name = args.index_name or settings.pinecone_kb_index_name
    cloud = args.cloud or settings.pinecone_cloud
    region = args.region or settings.pinecone_region

    bucket = settings.digitalocean_spaces_bucket
    prefix = args.prefix.lstrip("/")

    # 1) List objects
    objs = list_spaces_objects(bucket=bucket, prefix=prefix, limit=args.limit_files)
    if not objs:
        raise SystemExit(f"No objects found under s3://{bucket}/{prefix}")

    # 2) Create/reuse Pinecone index
    pc, host = ensure_pinecone_index(
        api_key=settings.pinecone_api_key,
        index_name=index_name,
        cloud=cloud,
        region=region,
        text_field=args.text_field,
    )
    idx = pc.Index(host=host)

    now = datetime.now(timezone.utc).isoformat()
    namespace = args.client_slug

    total_records = 0
    for o in objs:
        if not looks_texty(o.key):
            print(f"Skipping non-text file: {o.key}")
            continue
        text = get_spaces_object_text(bucket=bucket, key=o.key, max_bytes=args.max_bytes)
        if not text:
            print(f"Skipping empty file: {o.key}")
            continue

        fm = parse_yaml_frontmatter(text)
        content_type = fm.get("content_type") or "unknown"
        document_source = fm.get("document_source") or "unknown"
        source_url = fm.get("url") or ""
        title = fm.get("title") or ""

        body = strip_yaml_frontmatter(text)
        keywords: List[str] = []
        if args.add_keywords:
            try:
                # Late import so script can run without LLM deps if flag is off
                from app.clients.llm import llm_client  # noqa: WPS433

                cleaned = clean_for_keywords(body)[:2500]
                if cleaned:
                    system = (
                        "Extract 3-5 keywords or short keyphrases that best describe the document.\n"
                        "Return ONLY valid JSON.\n"
                        "Preferred format: {\"keywords\": [\"...\"]}\n"
                        "Allowed fallback: [\"...\"]\n"
                        "No punctuation except hyphens.\n"
                    )
                    user = f"Title: {title}\n\nBody:\n{cleaned}"
                    resp = asyncio.run(
                        llm_client.chat(
                            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                            temperature=0.2,
                            max_tokens=120,
                            model="gpt-4o-mini",
                        )
                    )
                    raw = resp["choices"][0]["message"]["content"].strip()
                    parsed: Any = None
                    try:
                        parsed = json.loads(raw)
                    except Exception:
                        # Try to extract the first JSON array/object substring if the model wrapped it in prose.
                        m = re.search(r"(\{[\\s\\S]*\\}|\\[[\\s\\S]*\\])", raw)
                        if m:
                            parsed = json.loads(m.group(1))

                    items: List[str] = []
                    if isinstance(parsed, dict) and isinstance(parsed.get("keywords"), list):
                        items = [x for x in parsed.get("keywords") if isinstance(x, str)]
                    elif isinstance(parsed, list):
                        items = [x for x in parsed if isinstance(x, str)]

                    keywords = [str(x).strip().lower() for x in items if str(x).strip()][:5]
            except Exception as e:
                print(f"Warning: keyword extraction failed for {o.key}: {e}")
                keywords = []

        chunks = chunk_text(body, chunk_size=args.chunk_size, overlap=args.overlap)

        records: List[Dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            rec_id = stable_id(namespace, o.key, str(i), chunk[:200])
            records.append(
                {
                    "_id": rec_id,
                    args.text_field: chunk,
                    # Flat metadata fields (filterable)
                    "client_slug": namespace,
                    "file_key": o.key,
                    "file_name": o.key.split("/")[-1],
                    "content_type": content_type,
                    "document_source": document_source,
                    "source_url": source_url,
                    "title": title,
                    "keywords": keywords,
                    "chunk_index": i,
                    "ingested_at": now,
                    "chunker": f"char:{args.chunk_size}:{args.overlap}",
                }
            )

        if args.dry_run:
            print(f"[DRY RUN] {o.key}: {len(chunks)} chunks -> {len(records)} records into {index_name}/{namespace}")
            continue

        # Pinecone constraint: text record batches <= 96 (per @pinecone-agents-ref)
        upserted = upsert_records_in_batches(idx, namespace=namespace, records=records, batch_size=96)
        total_records += upserted
        print(f"Upserted {upserted} records from {o.key} into index={index_name} namespace={namespace}")

    if not args.dry_run and total_records:
        # 3) Sanity: run one search
        from pinecone import SearchQuery

        resp = idx.search_records(
            namespace=namespace,
            query=SearchQuery(inputs={"text": "what does your company do?"}, top_k=3),
            fields=["*"],
        )
        print(f"\nSanity search returned {len(resp.result.hits) if hasattr(resp, 'result') else 'results'} hits")


if __name__ == "__main__":
    main()


