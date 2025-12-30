"""
Backfill Pinecone `keywords` metadata for chunk records where keywords are empty.

Strategy:
- Enumerate source files from DigitalOcean Spaces under a prefix.
- For each file, probe Pinecone (Records API) for an existing chunk for that spaces_key.
- If the returned chunk has `keywords == []` (or keywords missing), generate 3-5 keywords ONCE per file via LLM.
- Bulk-update all vectors for that spaces_key in the namespace using Pinecone `index.update(filter=..., set_metadata=...)`.

Why this approach:
- Avoids fetching dense vector values (expensive) to inspect metadata.
- Avoids re-upserting/chunking and preserves existing chunk IDs/content.
- Keywords are per-file, so updating by spaces_key is the natural unit of work.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import boto3

from app.config import get_settings


_MD_CODEBLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]+\)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_for_keywords(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    t = _MD_CODEBLOCK_RE.sub(" ", t)
    t = _MD_IMAGE_RE.sub(" ", t)
    t = _MD_LINK_RE.sub(r"\1", t)
    t = _MD_HTML_TAG_RE.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _looks_texty(key: str) -> bool:
    k = (key or "").lower()
    return any(
        k.endswith(ext)
        for ext in (
            ".md",
            ".markdown",
            ".txt",
            ".html",
            ".htm",
            ".json",
            ".csv",
            ".tsv",
            ".xml",
            ".yaml",
            ".yml",
        )
    )


def _spaces_s3_client():
    settings = get_settings()
    if not settings.digitalocean_spaces_key or not settings.digitalocean_spaces_secret:
        raise SystemExit("DIGITALOCEAN_SPACES_KEY/SECRET not configured")
    region = settings.digitalocean_spaces_region or "tor1"
    endpoint_url = f"https://{region}.digitaloceanspaces.com"
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.digitalocean_spaces_key,
        aws_secret_access_key=settings.digitalocean_spaces_secret,
    )


def list_spaces_keys(bucket: str, prefix: str, limit_files: Optional[int] = None) -> List[str]:
    s3 = _spaces_s3_client()
    out: List[str] = []
    token: Optional[str] = None
    while True:
        kwargs: Dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []) or []:
            key = obj.get("Key")
            if key:
                out.append(key)
                if limit_files and len(out) >= limit_files:
                    return out
        if resp.get("IsTruncated"):
            token = resp.get("NextContinuationToken")
        else:
            break
    return out


def get_spaces_object_text(bucket: str, key: str, max_bytes: int = 300_000) -> str:
    s3 = _spaces_s3_client()
    resp = s3.get_object(Bucket=bucket, Key=key)
    body = resp["Body"].read(max_bytes)
    try:
        return body.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _parse_keywords_from_llm(raw: str) -> List[str]:
    raw = (raw or "").strip()
    if not raw:
        return []

    parsed: Any = None
    try:
        parsed = json.loads(raw)
    except Exception:
        m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
        if m:
            parsed = json.loads(m.group(1))

    items: List[str] = []
    if isinstance(parsed, dict) and isinstance(parsed.get("keywords"), list):
        items = [x for x in parsed.get("keywords") if isinstance(x, str)]
    elif isinstance(parsed, list):
        items = [x for x in parsed if isinstance(x, str)]

    out: List[str] = []
    for item in items:
        s = item.strip().lower()
        if s:
            out.append(s)
    return out[:5]


async def _extract_keywords(title: str, body: str) -> List[str]:
    cleaned = _clean_for_keywords(body)[:2500]
    if not cleaned:
        return []

    # Late import so dry-run usage doesn't require OPENAI_API_KEY
    from app.clients.llm import llm_client  # noqa: WPS433

    system = (
        "Extract 3-5 keywords or short keyphrases that best describe the document.\n"
        "Return ONLY valid JSON.\n"
        "Preferred format: {\"keywords\": [\"...\"]}\n"
        "Allowed fallback: [\"...\"]\n"
        "Rules:\n"
        "- 3 to 5 items.\n"
        "- Lowercase.\n"
        "- No punctuation except hyphens.\n"
        "- Avoid generic words (home, page, click, welcome).\n"
    )
    user = f"Title: {(title or '').strip()}\n\nBody:\n{cleaned}"
    resp = await llm_client.chat(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=120,
        model="gpt-4o-mini",
    )
    raw = resp["choices"][0]["message"]["content"]
    return _parse_keywords_from_llm(raw)


def _probe_keywords_for_file(idx, namespace: str, spaces_key: str) -> Optional[List[str]]:
    """
    Probe Pinecone for one chunk for this spaces_key and return its keywords field.
    Returns:
      - list (possibly empty) if a hit exists
      - None if no record exists yet for that spaces_key
    """
    from pinecone import SearchQuery

    resp = idx.search_records(
        namespace=namespace,
        query=SearchQuery(
            inputs={"text": "keyword probe"},
            top_k=1,
            filter={"spaces_key": {"$eq": spaces_key}},
        ),
        fields=["spaces_key", "file_key", "keywords"],
    )
    hits = getattr(resp, "result", None) and getattr(resp.result, "hits", None)
    if not hits:
        return None
    h0 = resp.result.hits[0]
    fields = dict(h0.fields or {})
    kws = fields.get("keywords")
    if isinstance(kws, list) and all(isinstance(x, str) for x in kws):
        return kws
    if kws is None:
        return []
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Pinecone keywords for records with empty keywords")
    parser.add_argument("--client-slug", required=True, help="Client slug (Pinecone namespace)")
    parser.add_argument("--prefix", required=True, help="Spaces prefix, e.g. galactic-fed/")
    parser.add_argument("--index-name", default=None, help="Pinecone index name (default PINECONE_KB_INDEX)")
    parser.add_argument("--limit-files", type=int, default=None, help="Limit number of files scanned (debug)")
    parser.add_argument("--max-bytes", type=int, default=300_000, help="Max bytes to read per file for keyword generation")
    parser.add_argument("--dry-run", action="store_true", help="Don’t update Pinecone; just print what would happen")
    parser.add_argument("--force", action="store_true", help="Regenerate + overwrite keywords for ALL files (not only empty)")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.pinecone_api_key:
        raise SystemExit("PINECONE_API_KEY not configured")
    if not settings.digitalocean_spaces_bucket:
        raise SystemExit("DIGITALOCEAN_SPACES_BUCKET not configured")

    namespace = args.client_slug
    bucket = settings.digitalocean_spaces_bucket
    prefix = args.prefix.lstrip("/")
    index_name = args.index_name or settings.pinecone_kb_index_name

    # Connect to Pinecone index
    from pinecone import Pinecone

    pc = Pinecone(api_key=settings.pinecone_api_key)
    desc = pc.describe_index(index_name)
    idx = pc.Index(host=desc.host)

    keys = list_spaces_keys(bucket=bucket, prefix=prefix, limit_files=args.limit_files)
    keys = [k for k in keys if _looks_texty(k)]
    if not keys:
        raise SystemExit(f"No texty files found under s3://{bucket}/{prefix}")

    scanned = 0
    will_update = 0
    updated = 0
    skipped_no_record = 0
    skipped_has_keywords = 0
    errors = 0

    started_at = datetime.now(timezone.utc).isoformat()
    print(f"[start] {started_at} index={index_name} namespace={namespace} files={len(keys)} dry_run={args.dry_run} force={args.force}")

    for spaces_key in keys:
        scanned += 1

        try:
            existing = _probe_keywords_for_file(idx, namespace=namespace, spaces_key=spaces_key)
        except Exception as e:
            errors += 1
            print(f"[error] probe failed for {spaces_key}: {e}")
            continue

        if existing is None:
            # Not ingested yet (or different file_key in Pinecone)
            skipped_no_record += 1
            continue

        if (not args.force) and existing:
            skipped_has_keywords += 1
            continue

        # At this point: either keywords empty OR force overwrite
        will_update += 1
        if args.dry_run:
            print(f"[dry-run] would backfill keywords for {spaces_key}")
            continue

        try:
            text = get_spaces_object_text(bucket=bucket, key=spaces_key, max_bytes=args.max_bytes)
            if not text.strip():
                print(f"[warn] empty file, skipping: {spaces_key}")
                continue

            # Use filename as title fallback
            title = spaces_key.split("/")[-1]
            keywords = asyncio.run(_extract_keywords(title=title, body=text))
            if not keywords:
                print(f"[warn] no keywords generated, skipping update: {spaces_key}")
                continue

            # Bulk update all vectors for this spaces_key
            # NOTE: This merges metadata; it overwrites `keywords` while leaving other fields unchanged.
            idx.update(
                namespace=namespace,
                filter={"spaces_key": {"$eq": spaces_key}},
                set_metadata={"keywords": keywords},
            )
            updated += 1
            print(f"[ok] updated keywords for {spaces_key}: {keywords}")
        except Exception as e:
            errors += 1
            print(f"[error] update failed for {spaces_key}: {e}")

    finished_at = datetime.now(timezone.utc).isoformat()
    print(
        "[done]",
        {
            "finished_at": finished_at,
            "index": index_name,
            "namespace": namespace,
            "scanned_files": scanned,
            "would_update": will_update,
            "updated_files": updated,
            "skipped_no_record": skipped_no_record,
            "skipped_has_keywords": skipped_has_keywords,
            "errors": errors,
        },
    )


if __name__ == "__main__":
    main()


