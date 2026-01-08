#!/usr/bin/env python3
"""
Rebuild per-client metadata files in Supabase Storage.

For each client slug found in the shared bucket, writes:
  - {clientSlug}/supabase_storage_metadata.json
  - {clientSlug}/pinecone_namespace_metadata.json

Optionally deletes legacy:
  - {clientSlug}/metadata.json

This is intended to repair/standardize metadata after ingestion changes.

Usage (repo root, venv active):
  backend/venv/bin/python backend/scripts/rebuild_client_metadata_files.py

  # Single client
  backend/venv/bin/python backend/scripts/rebuild_client_metadata_files.py --client-slug mintleads

  # Process first N clients (for testing)
  backend/venv/bin/python backend/scripts/rebuild_client_metadata_files.py --limit 10
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path

# Ensure backend/ is on path when running from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.clients.supabase_storage_client import SupabaseStorageClient  # noqa: E402
from app.clients.pinecone_client import pinecone_kb_client  # noqa: E402


BUCKET_DEFAULT = "client-data-sources"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list_client_slugs(storage: SupabaseStorageClient, bucket: str) -> List[str]:
    """
    List top-level client slugs by looking for "folder" entries (metadata=None).
    Mirrors backend/app/routes/indexes.py behavior.
    """
    try:
        items = storage.list_objects(bucket, prefix="", limit=1000, offset=0, sort_by={"column": "name", "order": "asc"})
    except Exception:
        return []
    slugs: List[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        # folder entries: metadata=None
        if it.get("metadata") is not None:
            continue
        name = str(it.get("name") or "").strip().rstrip("/")
        if not name or name.startswith(".") or name.startswith("__"):
            continue
        slugs.append(name)
    return sorted(set(slugs))


def _walk_md_files(storage: SupabaseStorageClient, bucket: str, prefix: str) -> List[str]:
    """
    Recursively walk a prefix and return all .md object keys.
    Handles nested structures like website/pages/* created by onboarding scripts.
    """
    p = (prefix or "").strip().lstrip("/").rstrip("/")
    if not p:
        return []

    md_files: List[str] = []
    queue: List[str] = [p]
    seen: set[str] = set()

    while queue:
        current = queue.pop(0).strip().rstrip("/")
        if not current or current in seen:
            continue
        seen.add(current)

        list_prefix = f"{current}/"
        try:
            items = storage.list_objects(bucket, prefix=list_prefix, limit=1000, offset=0)
        except Exception:
            continue

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

            # File entry: normalize to full object key.
            full = name if name.startswith(f"{current}/") else f"{current}/{name}"
            if full.endswith(".md"):
                md_files.append(full)

    # De-dupe but preserve determinism
    return sorted(set(md_files))


def _parse_frontmatter(md: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown.
    Returns (frontmatter_dict, body_str).
    """
    s = (md or "")
    if not s.startswith("---"):
        return {}, s
    parts = s.split("---", 2)
    if len(parts) < 3:
        return {}, s
    try:
        import yaml

        meta = yaml.safe_load(parts[1]) or {}
        if not isinstance(meta, dict):
            meta = {}
    except Exception:
        meta = {}
    body = (parts[2] or "").strip()
    return meta, body


def _extract_existing_meta(storage: SupabaseStorageClient, bucket: str, slug: str) -> Dict[str, Any]:
    """
    Load any existing metadata sources BEFORE we overwrite/delete legacy files.
    Priority for favicon/title/url fields:
      - supabase_storage_metadata.json
      - pinecone_namespace_metadata.json
      - metadata.json (legacy)
    """
    candidates = [
        f"{slug}/supabase_storage_metadata.json",
        f"{slug}/pinecone_namespace_metadata.json",
        f"{slug}/metadata.json",
    ]
    for key in candidates:
        try:
            data = storage.download_json(bucket, key)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def _build_supabase_storage_metadata(
    *,
    storage: SupabaseStorageClient,
    bucket: str,
    slug: str,
    existing_meta: Dict[str, Any],
    default_chunker: str = "char:1200:200",
) -> Dict[str, Any]:
    """
    Build supabase_storage_metadata.json from Storage contents by parsing .md frontmatter.
    Uses existing_meta for favicon/title/url when available (since those are not guaranteed
    to be recoverable from markdown frontmatter alone).
    """
    website_by_ct: Dict[str, int] = {}
    drive_by_ct: Dict[str, int] = {}
    intake_count = 0

    # Collect markdown files across known roots (recursive)
    md_files: List[str] = []
    for subfolder in ["website", "drive", "intake_form"]:
        md_files.extend(_walk_md_files(storage, bucket, f"{slug}/{subfolder}"))
    md_files = sorted(set(md_files))

    # Walk + parse frontmatter for counts
    for key in md_files:
        try:
            raw = storage.download_bytes(bucket, key).decode("utf-8", errors="replace")
        except Exception:
            continue
        fm, _body = _parse_frontmatter(raw)
        ds = str(fm.get("document_source") or "unknown").strip() or "unknown"
        ct = str(fm.get("content_type") or "other").strip() or "other"
        if ds == "website":
            website_by_ct[ct] = website_by_ct.get(ct, 0) + 1
        elif ds in ("drive", "client_materials"):
            drive_by_ct[ct] = drive_by_ct.get(ct, 0) + 1
        elif ds in ("intake_form", "intake-form"):
            intake_count += 1

    # Prefer URLs + branding from existing meta (if present)
    website_url = str(existing_meta.get("website_url") or existing_meta.get("websiteUrl") or "") or ""
    drive_url = str(existing_meta.get("drive_url") or existing_meta.get("driveUrl") or "") or ""
    ui_meta = existing_meta.get("metadata") if isinstance(existing_meta.get("metadata"), dict) else {}
    if not isinstance(ui_meta, dict):
        ui_meta = {}

    title = str(ui_meta.get("title") or "") or slug
    favicon = ui_meta.get("favicon")
    favicon = str(favicon).strip() if isinstance(favicon, str) and favicon.strip() else None

    # Chunker: prefer existing chunker if present
    chunker = existing_meta.get("chunker") or (existing_meta.get("chunking") or {}).get("chunker")
    if not isinstance(chunker, str) or not chunker.strip():
        chunker = default_chunker
    chunker = str(chunker).strip()

    return {
        "website_url": website_url,
        "drive_url": drive_url,
        "client_slug": slug,
        "website_docs": {"total": sum(website_by_ct.values()), "by_content_type": dict(sorted(website_by_ct.items(), key=lambda x: (-x[1], x[0])))},
        "intake_form_docs": int(intake_count),
        "drive_docs": {"total": sum(drive_by_ct.values()), "by_content_type": dict(sorted(drive_by_ct.items(), key=lambda x: (-x[1], x[0])))},
        "createdAt": _utc_now_iso(),
        "metadata": {**({"title": title} if title else {}), **({"favicon": favicon} if favicon else {})},
        "chunker": chunker,
        "source": "supabase_storage",
        "debug": {
            "md_files_found": len(md_files),
        },
    }


def _build_pinecone_namespace_metadata(
    *,
    slug: str,
    website_url: str,
    drive_url: str,
    chunker: str,
    favicon: Optional[str],
) -> Dict[str, Any]:
    """
    Build pinecone_namespace_metadata.json from Pinecone namespace enumeration.
    Ensures favicon is present when available.
    """
    meta = pinecone_kb_client.build_onboarding_metadata_report(
        client_slug=slug,
        website_url=website_url,
        drive_url=drive_url,
        wait_after_upsert_s=0.0,
    )
    if not isinstance(meta, dict):
        meta = {"client_slug": slug, "website_url": website_url, "drive_url": drive_url}

    # Ensure nested metadata dict
    ui = meta.get("metadata")
    if not isinstance(ui, dict):
        ui = {}
        meta["metadata"] = ui
    if favicon and not ui.get("favicon"):
        ui["favicon"] = favicon

    meta["chunker"] = meta.get("chunker") or chunker
    meta["source"] = "pinecone_namespace"
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild per-client metadata files in Supabase Storage.")
    parser.add_argument("--bucket", default=BUCKET_DEFAULT, help="Supabase Storage bucket id.")
    parser.add_argument("--client-slug", default=None, help="Only process a single client slug.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N clients (for testing).")
    parser.add_argument("--delete-legacy", action="store_true", help="Delete {clientSlug}/metadata.json after writing new files.")
    parser.add_argument("--dry-run", action="store_true", help="Compute and print actions without uploading/deleting.")
    args = parser.parse_args()

    storage = SupabaseStorageClient()
    bucket = str(args.bucket).strip()

    slugs = [args.client_slug] if args.client_slug else _list_client_slugs(storage, bucket)
    if args.limit:
        slugs = slugs[: int(args.limit)]

    if not slugs:
        print("No client slugs found.")
        return 1

    print(f"Rebuilding metadata for {len(slugs)} client(s) in bucket={bucket!r}")
    print(f"- dry_run={bool(args.dry_run)}")
    print(f"- delete_legacy={bool(args.delete_legacy)}")

    ok = 0
    failed = 0
    deleted = 0

    for slug in slugs:
        s = (slug or "").strip()
        if not s:
            continue
        print("\n" + "=" * 80)
        print(f"client: {s}")

        try:
            existing = _extract_existing_meta(storage, bucket, s)
            supabase_meta = _build_supabase_storage_metadata(storage=storage, bucket=bucket, slug=s, existing_meta=existing)

            website_url = str(supabase_meta.get("website_url") or "")
            drive_url = str(supabase_meta.get("drive_url") or "")
            chunker = str(supabase_meta.get("chunker") or "char:1200:200")
            ui = supabase_meta.get("metadata") if isinstance(supabase_meta.get("metadata"), dict) else {}
            favicon = ui.get("favicon") if isinstance(ui, dict) else None
            favicon = str(favicon).strip() if isinstance(favicon, str) and favicon.strip() else None

            pinecone_meta = _build_pinecone_namespace_metadata(
                slug=s,
                website_url=website_url,
                drive_url=drive_url,
                chunker=chunker,
                favicon=favicon,
            )

            # Upload both
            if args.dry_run:
                print("would_upload:", f"{s}/supabase_storage_metadata.json")
                print("would_upload:", f"{s}/pinecone_namespace_metadata.json")
            else:
                storage.upload_json(bucket=bucket, path=f"{s}/supabase_storage_metadata.json", payload=supabase_meta, upsert=True)
                storage.upload_json(bucket=bucket, path=f"{s}/pinecone_namespace_metadata.json", payload=pinecone_meta, upsert=True)
                print("uploaded:", f"{s}/supabase_storage_metadata.json")
                print("uploaded:", f"{s}/pinecone_namespace_metadata.json")

            # Optionally delete legacy metadata.json
            if args.delete_legacy:
                legacy_key = f"{s}/metadata.json"
                try:
                    if args.dry_run:
                        print("would_delete:", legacy_key)
                    else:
                        if storage.object_exists(bucket, legacy_key):
                            storage.delete_objects(bucket, [legacy_key])
                            deleted += 1
                            print("deleted:", legacy_key)
                except Exception as e:
                    print("warn: could not delete legacy metadata.json:", e)

            ok += 1

        except Exception as e:  # noqa: BLE001
            failed += 1
            print("ERROR:", e)
            # keep going
            time.sleep(0.1)

    print("\n" + "=" * 80)
    print("Done.")
    print(f"- ok: {ok}")
    print(f"- failed: {failed}")
    print(f"- deleted_legacy: {deleted}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())


