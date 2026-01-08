from __future__ import annotations

import json
import hashlib
import time
import re
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, quote

from ..config import get_settings
from ..utils.content_hash import compute_content_hash


def _stable_id(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="ignore"))
        h.update(b"\0")
    return h.hexdigest()[:32]


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    text = (text or "").strip()
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
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _is_retryable_pinecone_error(e: Exception) -> bool:
    """
    Best-effort detection of Pinecone rate limiting / transient overload.
    Pinecone SDK exception types vary by transport/version, so we rely on message + common attrs.
    """
    s = str(e) or ""
    s_low = s.lower()
    if "429" in s_low or "too many requests" in s_low:
        return True
    if "resource_exhausted" in s_low:
        return True
    if "rate limit" in s_low:
        return True
    return False


def _retry_after_seconds(e: Exception) -> float | None:
    """
    Extract Retry-After seconds if present (best-effort).
    """
    # Some exception objects carry headers or response headers.
    for attr in ("headers", "response_headers", "responseHeaders"):
        h = getattr(e, attr, None)
        if isinstance(h, dict):
            ra = h.get("Retry-After") or h.get("retry-after")
            try:
                return float(ra)
            except Exception:
                pass
    # Fallback: parse from message
    m = re.search(r"retry-after[^0-9]*([0-9]+)", str(e), flags=re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    return None


def _sleep_with_jitter(base_s: float, *, jitter_ratio: float = 0.25) -> None:
    j = base_s * jitter_ratio
    delay = max(0.0, base_s + random.uniform(-j, j))
    time.sleep(delay)


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


def _split_markdown_blocks(md: str) -> List[str]:
    """
    Split markdown into "blocks" separated by blank lines.
    This tends to preserve lists/tables/code blocks better than line-by-line splitting.
    """
    t = (md or "").strip()
    if not t:
        return []
    # Normalize newlines and collapse excessive blank lines.
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)
    return [b.strip() for b in t.split("\n\n") if b.strip()]


def _chunk_markdown_semantic_v1(
    md: str,
    *,
    target_words: int = 350,
    max_words: int = 550,
    overlap_words: int = 80,
) -> List[str]:
    """
    Structure-aware chunking for markdown-ish content.

    Strategy:
    - Split into sections by headings (#..######)
    - Within each section, chunk on paragraph/list/table blocks
    - Enforce word-budget rather than raw characters
    - Carry a small overlap in terms of tail blocks
    """
    text = (md or "").strip()
    if not text:
        return []

    # Parse headings into sections
    heading_re = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    sections: List[Dict[str, Any]] = []
    heading_stack: List[Tuple[int, str]] = []
    cur_lines: List[str] = []

    def flush_section():
        nonlocal cur_lines
        body = "\n".join(cur_lines).strip()
        if not body:
            cur_lines = []
            return
        headings = "\n".join([("#" * lvl) + " " + title for (lvl, title) in heading_stack]).strip()
        prefix = (headings + "\n\n") if headings else ""
        sections.append({"prefix": prefix, "body": body})
        cur_lines = []

    for line in lines:
        m = heading_re.match(line.strip())
        if m:
            # start new section; commit previous
            flush_section()
            level = len(m.group(1))
            title = m.group(2).strip()
            # update stack for heading level
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            continue
        cur_lines.append(line)
    flush_section()

    # If no headings, treat whole doc as a single section.
    if not sections:
        sections = [{"prefix": "", "body": text}]

    out: List[str] = []

    for sec in sections:
        prefix: str = sec["prefix"]
        blocks = _split_markdown_blocks(sec["body"])
        if not blocks:
            continue

        cur_blocks: List[str] = []
        cur_words = 0
        tail_blocks: List[str] = []
        tail_words = 0

        def emit_current():
            nonlocal cur_blocks, cur_words, tail_blocks, tail_words
            if not cur_blocks:
                return
            chunk_body = "\n\n".join(cur_blocks).strip()
            if not chunk_body:
                return
            out.append((prefix + chunk_body).strip())
            # prepare overlap by taking tail blocks up to overlap_words
            tail_blocks = []
            tail_words = 0
            for b in reversed(cur_blocks):
                bw = _word_count(b)
                if tail_words + bw > overlap_words and tail_blocks:
                    break
                tail_blocks.insert(0, b)
                tail_words += bw
                if tail_words >= overlap_words:
                    break
            cur_blocks = []
            cur_words = 0

        for b in blocks:
            bw = _word_count(b)
            if bw == 0:
                continue

            # If this single block is enormous, fall back to char chunking within the block.
            if bw > max_words * 2:
                emit_current()
                # chunk the huge block itself
                # (use conservative char-size to avoid super-long chunks)
                for sub in _chunk_text(b, chunk_size=2000, overlap=250):
                    out.append((prefix + sub).strip())
                continue

            # Start chunk with overlap if we just emitted
            if not cur_blocks and tail_blocks:
                cur_blocks.extend(tail_blocks)
                cur_words = sum(_word_count(x) for x in tail_blocks)

            # If adding this block would exceed max_words, emit current chunk.
            if cur_blocks and (cur_words + bw) > max_words:
                emit_current()
                # start next chunk with overlap
                if tail_blocks:
                    cur_blocks.extend(tail_blocks)
                    cur_words = sum(_word_count(x) for x in tail_blocks)

            cur_blocks.append(b)
            cur_words += bw

            # If we've crossed target_words and we are at a natural boundary, emit.
            if cur_words >= target_words and (cur_words >= max_words or b.endswith((".", "!", "?", ":"))):
                emit_current()

        emit_current()

    return [c for c in out if c.strip()]


def _website_markdown_file_key(url: str) -> str:
    """
    Build a stable, human-readable per-page key for website documents.

    User requirement:
    - if document_source == "website" and content is markdown,
      file_key = "<domain>/<path>.md" where:
        - domain is the URL host without leading "www."
        - path is everything after the domain (e.g. "/email-campaign-management")
        - always ends with ".md"

    Example:
      url = "www.inboxarmy.com/email-campaign-management"
      => "inboxarmy.com/email-campaign-management.md"
    """
    u = (url or "").strip()
    if not u:
        return ""

    # urlparse needs a scheme to reliably parse netloc
    if "://" not in u:
        u = f"https://{u}"
    parsed = urlparse(u)

    host = (parsed.netloc or "").split("@")[-1].split(":")[0].strip().lower()
    if host.startswith("www."):
        host = host[4:]

    path = (parsed.path or "").strip()
    if not path or path == "/":
        path = "/index"
    # remove trailing slash
    if path.endswith("/"):
        path = path.rstrip("/")
        if not path:
            path = "/index"

    # Ensure .md extension (replace any existing extension on the last segment)
    last = path.rsplit("/", 1)[-1]
    if "." in last:
        base = last.rsplit(".", 1)[0]
        path = path[: -len(last)] + base
    if not path.endswith(".md"):
        path = f"{path}.md"

    return f"{host}{path}"


@dataclass(frozen=True)
class PineconeHit:
    record_id: str
    score: float
    fields: Dict[str, Any]


class PineconeKBClient:
    """
    Thin Pinecone wrapper for this app's KB workflows.

    Design choices:
    - One KB index per environment (e.g. sb-knowledge-bases), namespace per client_slug.
    - Integrated embedding via `create_index_for_model` + `upsert_records`.
    - Flat metadata only (no nested objects).
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._pc = None
        self._index_host_cache: Dict[str, str] = {}

    def _pc_client(self):
        if not self.settings.pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY is not configured")
        if self._pc is None:
            from pinecone import Pinecone

            self._pc = Pinecone(api_key=self.settings.pinecone_api_key)
        return self._pc

    def ensure_index(self, index_name: Optional[str] = None, text_field: str = "text") -> Tuple[str, str]:
        """
        Ensure the Pinecone index exists and return (index_name, host).
        """
        from pinecone import CloudProvider, AwsRegion, EmbedModel, IndexEmbed

        idx_name = index_name or self.settings.pinecone_kb_index_name
        if idx_name in self._index_host_cache:
            return idx_name, self._index_host_cache[idx_name]

        pc = self._pc_client()

        # Try describe first
        try:
            desc = pc.describe_index(idx_name)
            host = desc.host
            self._index_host_cache[idx_name] = host
            return idx_name, host
        except Exception:
            pass

        # Create if missing (AWS only for now)
        cloud_norm = (self.settings.pinecone_cloud or "aws").strip().lower()
        if cloud_norm != "aws":
            raise ValueError("Only Pinecone serverless AWS indexes are supported by this client (PINECONE_CLOUD=aws).")

        region_norm = (self.settings.pinecone_region or "us-east-1").strip().lower().replace("-", "_")
        aws_region = getattr(AwsRegion, region_norm.upper(), None)
        if aws_region is None:
            raise ValueError(f"Unsupported AWS region for Pinecone SDK enum: {self.settings.pinecone_region}")

        created = pc.create_index_for_model(
            name=idx_name,
            cloud=CloudProvider.AWS,
            region=aws_region,
            # NOTE: metric must be a string (None triggers PineconeApiTypeError)
            embed=IndexEmbed(model=EmbedModel.Multilingual_E5_Large, field_map={"text": text_field}, metric="cosine"),
        )
        host = created.host
        self._index_host_cache[idx_name] = host
        return idx_name, host

    def _index(self, index_name: Optional[str] = None, text_field: str = "text"):
        pc = self._pc_client()
        _, host = self.ensure_index(index_name=index_name, text_field=text_field)
        return pc.Index(host=host)

    def delete_records_by_file_key(
        self,
        *,
        client_slug: str,
        file_key: str,
        index_name: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Best-effort deletion of all records for a given file_key within a namespace.

        We store `file_key` as a flat metadata field on every record, so we can delete
        all chunks for a source file using a metadata filter.
        """
        ns = (namespace or client_slug or "").strip()
        fk = (file_key or "").strip()
        if not ns:
            raise ValueError("namespace/client_slug required")
        if not fk:
            raise ValueError("file_key required")

        idx = self._index(index_name=index_name or self.settings.pinecone_kb_index_name, text_field="text")
        try:
            # Pinecone delete supports metadata filters (Mongo-ish operators).
            idx.delete(namespace=ns, filter={"file_key": {"$eq": fk}})
            return {"deleted": True, "method": "filter", "namespace": ns, "file_key": fk, "index": index_name or self.settings.pinecone_kb_index_name}
        except Exception as e:
            return {"deleted": False, "error": str(e), "namespace": ns, "file_key": fk, "index": index_name or self.settings.pinecone_kb_index_name}

    def _reports_index(self):
        """
        Report docs live in the REPORTING namespace of the configured reports index.
        """
        return self._index(index_name=self.settings.pinecone_client_kb_reports_index_name, text_field="text")

    def upsert_client_report(self, *, client_slug: str, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert the per-client report into the REPORTING namespace using the required schema:
        - _id:        clients/{client_slug}
        - file_key:   client_kb_reports/{client_slug}.json
        - content_type:     REPORTS
        - document_source:  REPORTS
        """
        idx = self._reports_index()
        now = datetime.now(timezone.utc).isoformat()
        doc_id = f"clients/{client_slug}"
        file_key = f"client_kb_reports/{client_slug}.json"

        compact = json.dumps(report, separators=(",", ":"), ensure_ascii=False)
        idx.upsert_records(
            namespace=self.settings.pinecone_client_kb_reports_namespace,
            records=[
                {
                    "_id": doc_id,
                    "text": compact,
                    "client_slug": client_slug,
                    "file_key": file_key,
                    "content_type": "REPORTS",
                    "document_source": "REPORTS",
                    "generated_at": now,
                }
            ],
        )
        return {"upserted": True, "index": self.settings.pinecone_client_kb_reports_index_name, "namespace": self.settings.pinecone_client_kb_reports_namespace, "id": doc_id}

    def upsert_reports_summary(self, *, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert the global summary report into REPORTING.
        """
        idx = self._reports_index()
        now = datetime.now(timezone.utc).isoformat()
        doc_id = "summary"
        file_key = "client_kb_reports/summary.json"
        compact = json.dumps(summary, separators=(",", ":"), ensure_ascii=False)
        idx.upsert_records(
            namespace=self.settings.pinecone_client_kb_reports_namespace,
            records=[
                {
                    "_id": doc_id,
                    "text": compact,
                    "file_key": file_key,
                    "content_type": "REPORTS",
                    "document_source": "REPORTS",
                    "generated_at": now,
                }
            ],
        )
        return {"upserted": True, "index": self.settings.pinecone_client_kb_reports_index_name, "namespace": self.settings.pinecone_client_kb_reports_namespace, "id": doc_id}

    def upsert_documents(
        self,
        *,
        client_slug: str,
        documents: List[Dict[str, Any]],
        index_name: Optional[str] = None,
        text_field: str = "text",
        chunk_size: int = 1200,
        overlap: int = 200,
        chunker_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert documents to chunk records and upsert into Pinecone.

        Pinecone constraints (per @pinecone-agents-ref):
        - Namespace must be provided.
        - Text records batch size <= 96.
        - Flat metadata only.
        """
        namespace = client_slug
        idx = self._index(index_name=index_name, text_field=text_field)
        now = datetime.now(timezone.utc).isoformat()
        raw_chunker = (chunker_name or "").strip()
        chunker_sel = raw_chunker.lower()
        # Default: char-based windows
        chunker = raw_chunker or f"char:{chunk_size}:{overlap}"

        records: List[Dict[str, Any]] = []
        for doc in documents:
            # Pull text
            content = ""
            if isinstance(doc.get("markdown"), str):
                content = doc.get("markdown") or ""
            elif isinstance(doc.get("content"), str):
                content = doc.get("content") or ""
            else:
                # Sometimes content is {text: ...}
                c = doc.get("content") or {}
                if isinstance(c, dict) and isinstance(c.get("text"), str):
                    content = c.get("text") or ""

            content = content.strip()
            if not content:
                continue

            title = str(doc.get("title") or (doc.get("metadata") or {}).get("title") or "")
            url = str(doc.get("url") or (doc.get("metadata") or {}).get("url") or "")
            content_type = str(doc.get("content_type") or (doc.get("metadata") or {}).get("content_type") or "other")
            document_source = str(doc.get("document_source") or (doc.get("metadata") or {}).get("document_source") or "unknown")
            file_key = str(doc.get("file_key") or "")
            storage_bucket = str(doc.get("storage_bucket") or (doc.get("metadata") or {}).get("storage_bucket") or "client-data-sources")
            storage_path = str(doc.get("storage_path") or (doc.get("metadata") or {}).get("storage_path") or file_key or "")
            file_type = str(doc.get("file_type") or (doc.get("metadata") or {}).get("file_type") or "")
            document_context = str(doc.get("document_context") or (doc.get("metadata") or {}).get("document_context") or "").strip()
            # Flat, filterable favicon field (if available). Required for onboarding reports.
            # NOTE: must remain flat (no nested metadata objects) to keep Pinecone metadata filtering happy.
            favicon = None
            meta = doc.get("metadata") or {}
            if isinstance(doc.get("favicon"), str) and str(doc.get("favicon")).strip():
                favicon = str(doc.get("favicon")).strip()
            elif isinstance(meta, dict) and isinstance(meta.get("favicon"), str) and str(meta.get("favicon")).strip():
                favicon = str(meta.get("favicon")).strip()
            # Canonicalize website markdown file_key if not explicitly provided.
            if (not file_key) and document_source.strip().lower() == "website" and url:
                file_key = _website_markdown_file_key(url)
            if not file_key:
                # Fallback for non-website or missing URL.
                file_key = storage_path or url or title or "unknown"

            # Ensure original file type is present.
            if not file_type:
                if document_source.strip().lower() == "website":
                    file_type = "html"
            keywords = doc.get("keywords")
            if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
                keywords = []

            # ------------------------------------------------------------
            # Per-chunk prefix (requested): inject doc summary + keywords
            # ------------------------------------------------------------
            keywords_str = ", ".join([k.strip() for k in (keywords or []) if isinstance(k, str) and k.strip()])
            prefix = (
                "### DOCUMENT CONTEXT ###\n\n"
                f"DOCUMENT SUMMARY: {document_context}\n\n"
                f"DOCUMENT KEYWORDS: {keywords_str}\n\n"
                "#########################\n\n"
            )
            # If we have neither summary nor keywords, keep embeddings clean (no empty boilerplate).
            if not (document_context or keywords_str):
                prefix = ""

            # Hash the document body just before chunking (tracks content changes over time)
            content_hash = ""
            try:
                content_hash = str(doc.get("content_hash") or (doc.get("metadata") or {}).get("content_hash") or "").strip()
            except Exception:
                content_hash = ""
            if not content_hash:
                content_hash = compute_content_hash(content)

            # Chunking strategy (opt-in):
            # - default: char window
            # - semantic markdown: md_semantic_v1[:w350][:m550][:o80]
            if chunker_sel.startswith("md_semantic_v1"):
                # Parse optional params from chunker_name like "md_semantic_v1:w350:m550:o80"
                tw = 350
                mw = 550
                ow = 80
                m = re.search(r"w(\d+)", chunker_sel)
                if m:
                    tw = max(50, int(m.group(1)))
                m = re.search(r"m(\d+)", chunker_sel)
                if m:
                    mw = max(tw, int(m.group(1)))
                m = re.search(r"o(\d+)", chunker_sel)
                if m:
                    ow = max(0, int(m.group(1)))
                chunker = f"md_semantic_v1:w{tw}:m{mw}:o{ow}"
                # Account for the prefix so the total chunk stays closer to the target budgets.
                if prefix:
                    pw = _word_count(prefix)
                    tw_eff = max(50, tw - pw)
                    mw_eff = max(tw_eff, mw - pw)
                    chunks = _chunk_markdown_semantic_v1(content, target_words=tw_eff, max_words=mw_eff, overlap_words=ow)
                else:
                    chunks = _chunk_markdown_semantic_v1(content, target_words=tw, max_words=mw, overlap_words=ow)
            elif chunker_sel in ("char", "char_v1"):
                chunker = f"char:{chunk_size}:{overlap}"
                # Account for the prefix so final payload doesn't blow past model token limits.
                if prefix:
                    # Keep a minimum content window even for long prefixes.
                    budget = max(200, int(chunk_size) - len(prefix) - 50)
                    chunks = _chunk_text(content, chunk_size=budget, overlap=min(overlap, max(0, budget // 5)))
                else:
                    chunks = _chunk_text(content, chunk_size=chunk_size, overlap=overlap)
            elif chunker_sel.startswith("char:"):
                # If they pass explicit "char:1200:200", keep it (and still use our defaults for now)
                if prefix:
                    budget = max(200, int(chunk_size) - len(prefix) - 50)
                    chunks = _chunk_text(content, chunk_size=budget, overlap=min(overlap, max(0, budget // 5)))
                else:
                    chunks = _chunk_text(content, chunk_size=chunk_size, overlap=overlap)
            else:
                # Unknown chunker string -> safe fallback
                chunker = f"char:{chunk_size}:{overlap}"
                if prefix:
                    budget = max(200, int(chunk_size) - len(prefix) - 50)
                    chunks = _chunk_text(content, chunk_size=budget, overlap=min(overlap, max(0, budget // 5)))
                else:
                    chunks = _chunk_text(content, chunk_size=chunk_size, overlap=overlap)
            for i, chunk in enumerate(chunks):
                # Use file_key as the stable per-file identifier for record IDs
                id_seed = file_key or storage_path or url or title or "unknown"
                rec_id = _stable_id(namespace, id_seed, str(i), chunk[:200])
                # Preview URL into Supabase Storage (public URL form).
                preview_url = ""
                try:
                    project_url = str(self.settings.supabase_agent_url or self.settings.supabase_url or "").rstrip("/")
                    if project_url and storage_bucket and storage_path:
                        preview_url = f"{project_url}/storage/v1/object/public/{storage_bucket}/{quote(storage_path, safe='/')}"
                except Exception:
                    preview_url = ""
                # IMPORTANT: flat fields only (no nested metadata objects)
                records.append(
                    {
                        "_id": rec_id,
                        # Prefix is included in the embedded text (and thus search + retrieved context).
                        text_field: (prefix + chunk) if prefix else chunk,
                        "client_slug": namespace,
                        "file_key": file_key,
                        **({"favicon": favicon} if favicon else {}),
                        "storage_bucket": storage_bucket,
                        "storage_path": storage_path,
                        "storage_preview_url": preview_url,
                        "file_type": file_type,
                        "content_hash": content_hash,
                        "document_context": document_context,
                        "title": title,
                        "url": url,
                        "content_type": content_type,
                        "document_source": document_source,
                        "keywords": keywords,  # string list OK (flat)
                        "chunk_index": i,
                        "ingested_at": now,
                        "chunker": chunker,
                    }
                )

        # Batch upsert (MAX 96 records per request)
        total = 0
        batch_size = 96
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            # Rate limit handling: integrated embedding can hit tokens-per-minute caps.
            # Retry with exponential backoff + jitter; respect Retry-After when provided.
            max_retries = 8
            attempt = 0
            while True:
                try:
                    idx.upsert_records(namespace=namespace, records=batch)
                    break
                except Exception as e:
                    attempt += 1
                    if (attempt > max_retries) or (not _is_retryable_pinecone_error(e)):
                        raise
                    ra = _retry_after_seconds(e)
                    # If Pinecone indicates a TPM cap, waiting ~60s is usually required to recover.
                    if ra is None and "tokens per minute" in (str(e).lower()):
                        ra = 60.0
                    # Exponential backoff capped at 90s
                    backoff = min(90.0, (2.0 ** min(attempt, 6)))
                    wait_s = float(ra) if ra is not None else backoff
                    _sleep_with_jitter(wait_s, jitter_ratio=0.2)
            total += len(batch)

        return {
            "index": index_name or self.settings.pinecone_kb_index_name,
            "namespace": namespace,
            "records_upserted": total,
        }

    def build_onboarding_metadata_report(
        self,
        *,
        client_slug: str,
        website_url: str | None = None,
        drive_url: str | None = None,
        index_name: str | None = None,
        page_size: int = 99,
        max_pages: int = 10_000,
        wait_after_upsert_s: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Build a DO-style onboarding metadata report by enumerating *all* records
        in a client namespace and de-duping by `file_key`.

        Query strategy (per approved plan):
        - list_paginated(namespace=client_slug) to enumerate record IDs
        - fetch(ids=[...], namespace=client_slug) to retrieve flat metadata
        - dedupe by file_key to count distinct documents (not chunks)
        """
        if wait_after_upsert_s and wait_after_upsert_s > 0:
            time.sleep(wait_after_upsert_s)

        idx = self._index(index_name=index_name, text_field="text")
        namespace = client_slug

        # Pinecone list_paginated constraint: limit must be 1..99
        if page_size <= 0:
            page_size = 99
        if page_size >= 100:
            page_size = 99

        # file_key -> first-seen metadata snapshot
        docs: Dict[str, Dict[str, Any]] = {}
        earliest_ingested_at: str | None = None

        token: str | None = None
        pages = 0
        while True:
            pages += 1
            if pages > max_pages:
                break

            page = idx.list_paginated(namespace=namespace, limit=page_size, pagination_token=token)
            ids = [getattr(v, "id", None) for v in (getattr(page, "vectors", None) or [])]
            ids = [i for i in ids if isinstance(i, str) and i]
            if not ids:
                break

            fetched = idx.fetch(ids=ids, namespace=namespace)
            for _id, vec in (getattr(fetched, "vectors", None) or {}).items():
                md = getattr(vec, "metadata", None) or {}
                if not isinstance(md, dict):
                    continue

                file_key = str(md.get("storage_path") or md.get("file_key") or md.get("url") or _id or "").strip()
                if not file_key:
                    continue

                if file_key not in docs:
                    ds = str(md.get("document_source") or "unknown").strip() or "unknown"
                    ct = str(md.get("content_type") or "other").strip() or "other"
                    title = str(md.get("title") or "").strip()
                    favicon = md.get("favicon")
                    favicon = str(favicon).strip() if isinstance(favicon, str) and favicon.strip() else None

                    docs[file_key] = {
                        "document_source": ds,
                        "content_type": ct,
                        "title": title,
                        "favicon": favicon,
                        "url": str(md.get("url") or "").strip(),
                        "ingested_at": str(md.get("ingested_at") or "").strip(),
                    }

                ing = str(md.get("ingested_at") or "").strip()
                if ing and (earliest_ingested_at is None or ing < earliest_ingested_at):
                    earliest_ingested_at = ing

            token = getattr(getattr(page, "pagination", None), "next", None)
            if not token:
                break

        # Aggregate counts by distinct file_key
        website_by_ct: Dict[str, int] = {}
        drive_by_ct: Dict[str, int] = {}
        page_breakdowns: Dict[str, int] = {}

        website_keys: set[str] = set()
        drive_keys: set[str] = set()
        intake_keys: set[str] = set()

        homepage_title: str | None = None
        homepage_favicon: str | None = None

        drive_sources = {"drive", "client_materials"}
        intake_sources = {"intake_form", "intake-form"}
        homepage_cts = {"homepage", "home", "home page"}

        for fk, info in docs.items():
            ds = str(info.get("document_source") or "unknown").strip() or "unknown"
            ct = str(info.get("content_type") or "other").strip() or "other"

            # Combined breakdown key (requested): document_source + "_" + content_type
            bk = f"{ds}_{ct}"
            page_breakdowns[bk] = page_breakdowns.get(bk, 0) + 1

            if ds == "website":
                website_keys.add(fk)
                website_by_ct[ct] = website_by_ct.get(ct, 0) + 1
                if (ct in homepage_cts) and (homepage_title is None or homepage_favicon is None):
                    if not homepage_title and isinstance(info.get("title"), str) and info.get("title").strip():
                        homepage_title = info.get("title").strip()
                    if not homepage_favicon and isinstance(info.get("favicon"), str) and info.get("favicon").strip():
                        homepage_favicon = info.get("favicon").strip()
            elif ds in drive_sources:
                drive_keys.add(fk)
                drive_by_ct[ct] = drive_by_ct.get(ct, 0) + 1
            elif ds in intake_sources:
                intake_keys.add(fk)

        # Reasonable fallback title/favicon if homepage not found
        if not homepage_title:
            homepage_title = client_slug
        if not homepage_favicon:
            # try any website doc favicon
            for info in docs.values():
                if info.get("document_source") == "website" and isinstance(info.get("favicon"), str) and info.get("favicon").strip():
                    homepage_favicon = info.get("favicon").strip()
                    break

        created_at = earliest_ingested_at or datetime.now(timezone.utc).isoformat()

        return {
            "website_url": website_url,
            "drive_url": drive_url,
            "client_slug": client_slug,
            "website_docs": {
                "total": len(website_keys),
                "by_content_type": dict(sorted(website_by_ct.items(), key=lambda x: (-x[1], x[0]))),
            },
            "intake_form_docs": len(intake_keys),
            "drive_docs": {
                "total": len(drive_keys),
                "by_content_type": dict(sorted(drive_by_ct.items(), key=lambda x: (-x[1], x[0]))),
            },
            "page_breakdowns": dict(sorted(page_breakdowns.items(), key=lambda x: (-x[1], x[0]))),
            "createdAt": created_at,
            "metadata": {
                "title": homepage_title,
                **({"favicon": homepage_favicon} if homepage_favicon else {}),
            },
        }

    def search(
        self,
        *,
        client_slug: str,
        query: str,
        top_k: int = 5,
        index_name: Optional[str] = None,
        text_field: str = "text",
        filter: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        wait_after_upsert_s: float = 0.0,
    ) -> List[PineconeHit]:
        """
        Search records for a client namespace. Returns hits with fields.
        """
        if wait_after_upsert_s and wait_after_upsert_s > 0:
            time.sleep(wait_after_upsert_s)

        from pinecone import SearchQuery

        idx = self._index(index_name=index_name, text_field=text_field)
        namespace = client_slug

        q = SearchQuery(inputs={"text": query}, top_k=top_k, filter=filter)
        resp = idx.search_records(
            namespace=namespace,
            query=q,
            fields=fields or ["*"],
        )

        hits: List[PineconeHit] = []
        for h in resp.result.hits:
            hits.append(
                PineconeHit(
                    record_id=h._id,
                    score=h._score,
                    fields=dict(h.fields or {}),
                )
            )
        return hits


pinecone_kb_client = PineconeKBClient()


