#!/usr/bin/env python3
"""
DELETE ALL CLIENTS across:
  - Supabase Storage (bucket: client-data-sources, prefix: {clientSlug}/...)
  - Pinecone KB index (namespace: {clientSlug})
  - Supabase DB tables: public.documents + public.clients (by client_slug)

This is intentionally destructive. Use --confirm to actually delete.

Usage (repo root, venv active):
  backend/venv/bin/python backend/scripts/delete_all_clients.py --dry-run

  backend/venv/bin/python backend/scripts/delete_all_clients.py --confirm DELETE_ALL_CLIENTS

  # limit for testing
  backend/venv/bin/python backend/scripts/delete_all_clients.py --confirm DELETE_ALL_CLIENTS --limit 5
"""

from __future__ import annotations

import argparse
import time
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# Ensure backend/ is on path when running from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.clients.supabase_storage_client import SupabaseStorageClient  # noqa: E402
from app.clients.supabase_agents_db_client import SupabaseAgentsDbClient  # noqa: E402
from app.config import get_settings  # noqa: E402


BUCKET = "client-data-sources"
INDEXES_SUMMARY_KEY = "__reports/indexes.json"


def _list_client_slugs(storage: SupabaseStorageClient) -> List[str]:
    """
    List top-level client slugs by looking for "folder" entries (metadata=None).
    """
    items = storage.list_objects(BUCKET, prefix="", limit=1000, offset=0, sort_by={"column": "name", "order": "asc"})
    slugs: List[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("metadata") is not None:
            continue
        name = str(it.get("name") or "").strip().rstrip("/")
        if not name or name.startswith(".") or name.startswith("__"):
            continue
        slugs.append(name)
    return sorted(set(slugs))


def _delete_storage_prefix(*, storage: SupabaseStorageClient, prefix: str, dry_run: bool) -> Dict[str, Any]:
    """
    Delete all objects under a prefix in a bucket.
    Supabase "folders" are prefixes; there is no separate folder delete.
    """
    p = (prefix or "").strip().lstrip("/").rstrip("/")
    if not p:
        raise ValueError("prefix required")

    deleted = 0
    listed_files = 0
    visited_prefixes = 0

    # Supabase list_objects is not recursive. Traverse prefixes breadth-first.
    queue: List[str] = [p]
    seen: set[str] = set()

    while queue:
        current = queue.pop(0).strip().rstrip("/")
        if not current or current in seen:
            continue
        seen.add(current)
        visited_prefixes += 1

        list_prefix = f"{current}/"
        items = storage.list_objects(BUCKET, prefix=list_prefix, limit=1000, offset=0)
        if not items:
            continue

        file_paths: List[str] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            name = str(it.get("name") or "").strip().lstrip("/").rstrip("/")
            if not name:
                continue

            meta = it.get("metadata")
            # Folder entry (metadata=None): enqueue deeper prefix.
            if meta is None:
                child = name if name.startswith(f"{current}/") else f"{current}/{name}"
                child = child.strip().rstrip("/")
                if child and child not in seen and child not in queue:
                    queue.append(child)
                continue

            # File entry: delete the full object key.
            listed_files += 1
            full = name if name.startswith(f"{current}/") else f"{current}/{name}"
            file_paths.append(full)

        if file_paths:
            if dry_run:
                deleted += len(file_paths)
            else:
                storage.delete_objects(BUCKET, file_paths)
                deleted += len(file_paths)

    return {
        "bucket": BUCKET,
        "prefix": f"{p}/",
        "visited_prefixes": visited_prefixes,
        "listed_files": listed_files,
        "deleted_objects": deleted,
        "dry_run": dry_run,
    }


def _delete_pinecone_namespace(*, index_name: str, namespace: str, dry_run: bool) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.pinecone_api_key:
        return {"deleted": False, "skipped": True, "reason": "PINECONE_API_KEY not configured"}
    if dry_run:
        return {"deleted": True, "dry_run": True, "index": index_name, "namespace": namespace}

    from pinecone import Pinecone

    pc = Pinecone(api_key=settings.pinecone_api_key)
    desc = pc.describe_index(index_name)
    idx = pc.Index(host=desc.host)
    try:
        idx.delete_namespace(namespace=namespace)
        return {"deleted": True, "method": "delete_namespace", "index": index_name, "namespace": namespace}
    except Exception:
        pass
    try:
        idx.delete(delete_all=True, namespace=namespace)
        return {"deleted": True, "method": "delete_all", "index": index_name, "namespace": namespace}
    except Exception as e:
        return {"deleted": False, "error": str(e), "index": index_name, "namespace": namespace}


async def _delete_db_rows(*, db: SupabaseAgentsDbClient, client_slug: str, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {"deleted": True, "dry_run": True}
    out: Dict[str, Any] = {"skipped": False}
    # Delete documents first (FK safety), then client.
    docs_res = await db.delete_documents_for_client(client_slug=client_slug)
    client_res = await db.delete_client(client_slug=client_slug)
    out["documents"] = docs_res
    out["clients"] = client_res
    out["deleted"] = True
    return out


async def main() -> int:
    parser = argparse.ArgumentParser(description="Delete ALL clients across Storage + Pinecone + DB.")
    parser.add_argument("--confirm", default=None, help='Must equal "DELETE_ALL_CLIENTS" to actually delete.')
    parser.add_argument("--dry-run", action="store_true", help="Do not delete anything; just print what would happen.")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N clients (for testing).")
    parser.add_argument("--skip-storage", action="store_true", help="Skip deleting Supabase Storage.")
    parser.add_argument("--skip-pinecone", action="store_true", help="Skip deleting Pinecone namespaces.")
    parser.add_argument("--skip-db", action="store_true", help="Skip deleting Supabase DB rows.")
    args = parser.parse_args()

    dry_run = bool(args.dry_run) or (str(args.confirm or "") != "DELETE_ALL_CLIENTS")
    if dry_run and not args.dry_run:
        print('Not deleting because --confirm is missing/incorrect. To delete, pass --confirm "DELETE_ALL_CLIENTS".')

    storage = SupabaseStorageClient()
    slugs = _list_client_slugs(storage)
    if args.limit:
        slugs = slugs[: int(args.limit)]

    if not slugs:
        print("No client slugs found in Storage.")
        return 1

    settings = get_settings()
    index_name = settings.pinecone_kb_index_name

    db: Optional[SupabaseAgentsDbClient] = None
    if not args.skip_db:
        try:
            db = SupabaseAgentsDbClient()
        except Exception as e:
            print("WARN: Supabase DB client not configured, skipping DB deletes:", e)
            db = None

    print("=" * 88)
    print("DELETE ALL CLIENTS")
    print("=" * 88)
    print(f"- bucket: {BUCKET}")
    print(f"- pinecone_kb_index: {index_name}")
    print(f"- clients_found: {len(slugs)}")
    print(f"- dry_run: {dry_run}")
    print(f"- skip_storage: {bool(args.skip_storage)}")
    print(f"- skip_pinecone: {bool(args.skip_pinecone)}")
    print(f"- skip_db: {bool(args.skip_db) or db is None}")

    # Best-effort delete of aggregated indexes summary (so UI regenerates).
    if not args.skip_storage:
        try:
            if dry_run:
                print(f"would_delete: {INDEXES_SUMMARY_KEY}")
            else:
                if storage.object_exists(BUCKET, INDEXES_SUMMARY_KEY):
                    storage.delete_objects(BUCKET, [INDEXES_SUMMARY_KEY])
                    print(f"deleted: {INDEXES_SUMMARY_KEY}")
        except Exception as e:
            print("WARN: could not delete indexes summary:", e)

    ok = 0
    failed = 0

    for slug in slugs:
        s = (slug or "").strip()
        if not s:
            continue
        print("\n" + "-" * 80)
        print(f"client: {s}")
        try:
            if not args.skip_storage:
                res = _delete_storage_prefix(storage=storage, prefix=s, dry_run=dry_run)
                print("storage:", res)
            if not args.skip_pinecone:
                res = _delete_pinecone_namespace(index_name=index_name, namespace=s, dry_run=dry_run)
                print("pinecone:", res)
            if db is not None and not args.skip_db:
                res = await _delete_db_rows(db=db, client_slug=s, dry_run=dry_run)
                print("db:", res)
            ok += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("ERROR:", e)
            # keep going
            time.sleep(0.1)

    print("\n" + "=" * 88)
    print("Done.")
    print(f"- ok: {ok}")
    print(f"- failed: {failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(__import__("asyncio").run(main()))


