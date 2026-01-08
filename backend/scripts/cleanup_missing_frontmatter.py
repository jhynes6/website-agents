#!/usr/bin/env python3
"""
Delete documents that are missing required YAML frontmatter fields:
  - document_context
  - keywords

Deletes across:
  - Supabase Storage object (bucket client-data-sources)
  - Supabase DB row in public.documents (by doc_id)
  - Pinecone chunks (by file_key filter within namespace)

Safety:
  - dry-run by default
  - requires --confirm to perform deletions
  - supports --client-slug to scope to one client
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml  # type: ignore

# Allow running as a standalone script from repo root (or anywhere) without
# requiring the caller to set PYTHONPATH=backend.
_THIS_FILE = Path(__file__).resolve()
_BACKEND_DIR = _THIS_FILE.parents[1]  # .../backend
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.clients.pinecone_client import pinecone_kb_client  # noqa: E402
from app.clients.supabase_agents_db_client import SupabaseAgentsDbClient  # noqa: E402
from app.clients.supabase_storage_client import SupabaseStorageClient  # noqa: E402


BUCKET = "client-data-sources"


@dataclass(frozen=True)
class Candidate:
    client_slug: str
    storage_path: str
    doc_id: str
    has_document_context: bool
    has_keywords: bool
    parse_error: Optional[str] = None


def _extract_frontmatter(md_text: str) -> Tuple[Optional[str], str]:
    """
    Return (frontmatter_yaml, body).
    """
    s = (md_text or "")
    if not s.startswith("---"):
        return None, s
    # split on the second '---' delimiter
    parts = s.split("\n---", 1)
    if len(parts) < 2:
        return None, s
    # parts[0] contains leading '---' + yaml; remove first '---\n'
    first = s.split("\n", 1)
    rest = first[1] if len(first) == 2 else ""
    # Now rest starts with yaml and then '\n---...'
    parts2 = rest.split("\n---", 1)
    if len(parts2) < 2:
        return None, s
    yaml_block = parts2[0]
    body = parts2[1]
    # body may start with newline(s)
    body = body.lstrip("\n")
    return yaml_block, body


def _parse_doc_id_from_frontmatter(raw_yaml: str) -> Optional[str]:
    if not raw_yaml:
        return None
    # yaml safe load first
    try:
        obj = yaml.safe_load(raw_yaml)
        if isinstance(obj, dict):
            v = obj.get("doc_id")
            if isinstance(v, str) and v.strip():
                return v.strip()
    except Exception:
        pass
    # fallback regex
    m = re.search(r'(?m)^\s*doc_id:\s*"([^"]+)"\s*$', raw_yaml)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?m)^\s*doc_id:\s*([^\n#]+)\s*$", raw_yaml)
    if m:
        return m.group(1).strip().strip('"').strip("'")
    return None


def _parse_storage_path_from_frontmatter(raw_yaml: str) -> Optional[str]:
    if not raw_yaml:
        return None
    # yaml safe load first
    try:
        obj = yaml.safe_load(raw_yaml)
        if isinstance(obj, dict):
            v = obj.get("storage_path")
            if isinstance(v, str) and v.strip():
                return v.strip().lstrip("/")
    except Exception:
        pass
    # fallback regex
    m = re.search(r'(?m)^\s*storage_path:\s*"([^"]+)"\s*$', raw_yaml)
    if m:
        return m.group(1).strip().lstrip("/")
    m = re.search(r"(?m)^\s*storage_path:\s*([^\n#]+)\s*$", raw_yaml)
    if m:
        return m.group(1).strip().strip('"').strip("'").lstrip("/")
    return None


def _default_storage_path(*, client_slug: str, document_source: str, doc_id: str) -> str:
    slug = (client_slug or "").strip()
    src = (document_source or "").strip()
    did = (doc_id or "").strip()
    # Match our create.py folder mapping
    folder = src
    if src in ("intake_form", "intake-form"):
        folder = "intake_form"
    elif src in ("drive", "client_materials"):
        folder = "drive"
    if not folder:
        folder = "website"
    return f"{slug}/{folder}/{did}"


def _has_nonempty_field(obj: Any, key: str) -> bool:
    if not isinstance(obj, dict):
        return False
    v = obj.get(key)
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return any(isinstance(x, str) and x.strip() for x in v) or len(v) > 0
    return True


def _frontmatter_fields_ok(raw_yaml: Optional[str]) -> Tuple[bool, bool, Optional[str]]:
    """
    Returns (has_document_context, has_keywords, parse_error)
    """
    if not raw_yaml:
        return False, False, None
    try:
        obj = yaml.safe_load(raw_yaml)
    except Exception as e:
        return False, False, str(e)
    has_ctx = _has_nonempty_field(obj, "document_context")
    has_kw = _has_nonempty_field(obj, "keywords")
    return has_ctx, has_kw, None


def _iter_all_objects(storage: SupabaseStorageClient, *, prefix: str) -> List[str]:
    """
    Return full object paths under a prefix.

    Supabase Storage list can return "folder" entries where `metadata` is null.
    We walk prefixes breadth-first to ensure nested paths (e.g. {slug}/website/...) are included.
    """
    root = (prefix or "").strip().strip("/")
    if not root:
        return []

    out: List[str] = []
    queue: List[str] = [root]
    visited: set[str] = set()

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        offset = 0
        limit = 1000
        while True:
            items = storage.list_objects(BUCKET, prefix=current, limit=limit, offset=offset)
            if not items:
                break

            for it in items:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name") or "")
                if not name:
                    continue
                meta = it.get("metadata")

                # folder entry
                if meta is None:
                    child = name if name.startswith(f"{current}/") else f"{current}/{name}"
                    queue.append(child.rstrip("/"))
                    continue

                # file entry
                full = name if name.startswith(f"{current}/") else f"{current}/{name}"
                out.append(full)

            if len(items) < limit:
                break
            offset += limit

    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-slug", default="", help="Optional: only process one client slug")
    ap.add_argument("--from-db", action="store_true", help="Use DB query (documents table) instead of reading Storage to find candidates")
    ap.add_argument("--require-document-context", action="store_true", default=True, help="(DB mode) treat document_context NULL as missing")
    ap.add_argument("--no-require-document-context", action="store_false", dest="require_document_context", help="(DB mode) don't require document_context")
    ap.add_argument("--require-keywords", action="store_true", default=True, help="(DB mode) treat keywords NULL/empty as missing")
    ap.add_argument("--no-require-keywords", action="store_false", dest="require_keywords", help="(DB mode) don't require keywords")
    ap.add_argument("--confirm", action="store_true", help="Actually delete (otherwise dry-run)")
    ap.add_argument("--limit", type=int, default=0, help="Optional: stop after N deletions candidates (0=all)")
    ap.add_argument("--include-semantic", action="store_true", help="Also attempt deletes in {client_slug}-semantic namespace")
    args = ap.parse_args()

    storage = SupabaseStorageClient()
    db = SupabaseAgentsDbClient()

    target_slug = (args.client_slug or "").strip()
    prefixes: List[str] = []
    if target_slug:
        prefixes = [target_slug]
    else:
        # discover client prefixes from bucket root
        root_items = storage.list_objects(BUCKET, prefix="", limit=1000, offset=0)
        seen: set[str] = set()
        for it in root_items:
            if not isinstance(it, dict):
                continue
            name = str(it.get("name") or "")
            if not name or "/" not in name:
                continue
            slug = name.split("/", 1)[0].strip()
            if slug:
                seen.add(slug)
        prefixes = sorted(seen)

    candidates: List[Candidate] = []

    if args.from_db:
        # DB-driven: faster and authoritative for "document_context is NULL" etc.
        # Also avoids downloading every Storage object.
        rows: List[Dict[str, Any]] = []
        for slug in prefixes:
            rows.extend(
                await db.list_documents_missing_fields(
                    client_slug=slug,
                    require_document_context=bool(args.require_document_context),
                    require_keywords=bool(args.require_keywords),
                    limit=int(args.limit) if args.limit else 10_000,
                )
            )
            if args.limit and len(rows) >= int(args.limit):
                rows = rows[: int(args.limit)]
                break

        for r in rows:
            slug = str(r.get("client_slug") or "").strip() or target_slug
            doc_id = str(r.get("doc_id") or "").strip()
            src = str(r.get("document_source") or "").strip()
            mh = r.get("metadata_header")
            mh = str(mh) if isinstance(mh, str) else ""
            storage_path = _parse_storage_path_from_frontmatter(mh) or _default_storage_path(client_slug=slug, document_source=src, doc_id=doc_id)
            has_ctx = bool(isinstance(r.get("document_context"), str) and str(r.get("document_context")).strip())
            kw = r.get("keywords")
            has_kw = bool(isinstance(kw, str) and str(kw).strip())
            candidates.append(
                Candidate(
                    client_slug=slug,
                    storage_path=storage_path,
                    doc_id=doc_id,
                    has_document_context=has_ctx,
                    has_keywords=has_kw,
                    parse_error=None,
                )
            )
    else:
        # Storage-driven: inspect YAML frontmatter in each .md object.
        for slug in prefixes:
            paths = _iter_all_objects(storage, prefix=slug)
            for p in paths:
                if not p.endswith(".md"):
                    continue
                # skip special/metadata objects
                if p.endswith("/.keep"):
                    continue
                if p.endswith("/pinecone_namespace_metadata.json") or p.endswith("/supabase_storage_metadata.json") or p.endswith("/metadata.json"):
                    continue
                raw = storage.download_bytes(BUCKET, p)
                text = raw.decode("utf-8", errors="replace")
                fm, _ = _extract_frontmatter(text)
                has_ctx, has_kw, parse_err = _frontmatter_fields_ok(fm)
                if has_ctx and has_kw:
                    continue
                doc_id = _parse_doc_id_from_frontmatter(fm or "") or p.split("/")[-1]
                candidates.append(
                    Candidate(
                        client_slug=slug,
                        storage_path=p,
                        doc_id=doc_id,
                        has_document_context=has_ctx,
                        has_keywords=has_kw,
                        parse_error=parse_err,
                    )
                )
                if args.limit and len(candidates) >= int(args.limit):
                    break
            if args.limit and len(candidates) >= int(args.limit):
                break

    print(f"Found {len(candidates)} candidates missing document_context or keywords")
    if not candidates:
        return

    # Dry-run preview
    for c in candidates[:25]:
        print(f"- {c.client_slug} | {c.doc_id} | {c.storage_path} | ctx={c.has_document_context} kw={c.has_keywords}")
    if len(candidates) > 25:
        print(f"... and {len(candidates)-25} more")

    if not args.confirm:
        print("Dry-run only. Re-run with --confirm to delete.")
        return

    # Execute deletions
    doc_ids = [c.doc_id for c in candidates]
    storage_paths = [c.storage_path for c in candidates]

    # 1) Supabase DB delete
    try:
        res_db = await db.delete_documents_by_doc_ids(doc_ids=doc_ids)
        print(f"Deleted documents rows: {res_db}")
    except Exception as e:
        print(f"ERROR deleting documents rows: {e}")

    # 2) Supabase Storage delete
    try:
        # Storage batch delete supports up to many prefixes; keep chunks manageable.
        chunk = 200
        for i in range(0, len(storage_paths), chunk):
            storage.delete_objects(BUCKET, storage_paths[i : i + chunk])
        print(f"Deleted {len(storage_paths)} storage objects")
    except Exception as e:
        print(f"ERROR deleting storage objects: {e}")

    # 3) Pinecone delete (best-effort per file_key within namespace)
    idx_name = None  # default configured kb index
    for c in candidates:
        namespaces = [c.client_slug]
        if args.include_semantic:
            namespaces.append(f"{c.client_slug}-semantic")
        for ns in namespaces:
            try:
                out = pinecone_kb_client.delete_records_by_file_key(
                    client_slug=c.client_slug,
                    namespace=ns,
                    index_name=idx_name,
                    file_key=c.storage_path,
                )
                if not out.get("deleted"):
                    print(f"Pinecone delete failed: ns={ns} file_key={c.storage_path} err={out.get('error')}")
            except Exception as e:
                print(f"Pinecone delete exception: ns={ns} file_key={c.storage_path} err={e}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())


