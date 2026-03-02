#!/usr/bin/env python3
"""
One-time utility to reformat existing intake form markdown files in Supabase Storage.

What it does:
1) Finds intake_form markdown files under client-data-sources/{client_slug}/intake_form/
2) Rewrites body content into the new structured format used by drive_ingest
3) Updates frontmatter content_hash
4) Uploads rewritten files back to Supabase (unless --dry-run)

Optional:
- --reembed: run upsert_to_pinecone.py --client <slug> after rewrites

Usage:
  python backend/scripts/reformat_intake_forms.py --client carol-mcleod-design --dry-run
  python backend/scripts/reformat_intake_forms.py --client carol-mcleod-design --reembed
  python backend/scripts/reformat_intake_forms.py --all --limit 5
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.config import get_settings  # noqa: E402
from app.clients.supabase_storage_client import SupabaseStorageClient  # noqa: E402
from app.services.drive_ingest import _format_intake_form_markdown  # noqa: E402
from app.utils.content_hash import compute_content_hash  # noqa: E402

BUCKET = "client-data-sources"


def _resolve_supabase_storage_key(settings) -> str:
    v = (os.getenv("SUPABASE_AGENT_SERVICE_ROLE_KEY") or "").strip()
    if v:
        return v
    v = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if v:
        return v
    return str(getattr(settings, "supabase_agent_key", "") or "").strip()


def _get_storage_client() -> SupabaseStorageClient:
    settings = get_settings()
    api_key = _resolve_supabase_storage_key(settings)
    return SupabaseStorageClient(project_url=str(settings.supabase_agent_url or ""), service_role_key=api_key)


def _list_client_slugs(storage: SupabaseStorageClient) -> List[str]:
    items = storage.list_objects(BUCKET, prefix="", limit=1000, offset=0, sort_by={"column": "name", "order": "asc"})
    slugs: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("metadata") is not None:
            continue
        name = str(item.get("name") or "").strip().rstrip("/")
        if not name or name.startswith(".") or name.startswith("__"):
            continue
        slugs.append(name)
    return sorted(set(slugs))


def _full_object_path(*, slug: str, prefix: str, item_name: str) -> str:
    n = (item_name or "").strip().lstrip("/")
    if not n:
        return ""
    if n.startswith(f"{slug}/"):
        return n
    if n.startswith("intake_form/"):
        return f"{slug}/{n}"
    return f"{prefix.rstrip('/')}/{n}"


def _parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str, bool]:
    t = text or ""
    if not t.startswith("---"):
        return {}, t, False
    parts = t.split("---", 2)
    if len(parts) < 3:
        return {}, t, False
    fm_raw = parts[1]
    body = parts[2].lstrip("\n")
    try:
        meta = yaml.safe_load(fm_raw) or {}
        if not isinstance(meta, dict):
            meta = {}
    except Exception:
        meta = {}
    return meta, body, True


def _build_markdown(meta: Dict[str, Any], body: str, has_frontmatter: bool) -> str:
    if not has_frontmatter:
        return body.strip() + "\n"
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=False).strip()
    return f"---\n{fm}\n---\n\n{body.strip()}\n"


def _is_intake_form_doc(*, object_path: str, meta: Dict[str, Any]) -> bool:
    src = str(meta.get("document_source") or "").strip().lower()
    if src in ("intake_form", "intake-form"):
        return True
    ct = str(meta.get("content_type") or "").strip().lower()
    if ct in ("intake_form", "intake-form"):
        return True
    return "/intake_form/" in object_path


def _run_reembed_for_client(client_slug: str) -> int:
    script = Path(__file__).resolve().parent / "upsert_to_pinecone.py"
    cmd = [sys.executable, str(script), "--client", client_slug]
    print(f"\n🔁 Re-embedding client: {client_slug}")
    print(" ".join(cmd))
    return subprocess.call(cmd)


def reformat_client(*, storage: SupabaseStorageClient, client_slug: str, dry_run: bool) -> Dict[str, Any]:
    md_paths: List[str] = []
    for subfolder in ("intake_form", "drive"):
        prefix = f"{client_slug}/{subfolder}"
        items = storage.list_objects(BUCKET, prefix=prefix, limit=1000, offset=0, sort_by={"column": "name", "order": "asc"})
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("metadata") is None:
                continue
            if not str(item.get("name") or "").endswith(".md"):
                continue
            object_path = _full_object_path(slug=client_slug, prefix=prefix, item_name=str(item.get("name") or ""))
            if object_path:
                md_paths.append(object_path)
    md_paths = sorted(set(md_paths))

    scanned = 0
    changed = 0
    skipped = 0
    errors = 0

    for object_path in md_paths:
        scanned += 1

        try:
            raw = storage.download_bytes(BUCKET, object_path)
            original = raw.decode("utf-8", errors="ignore")
            meta, body, has_fm = _parse_frontmatter(original)
            if not _is_intake_form_doc(object_path=object_path, meta=meta):
                skipped += 1
                continue

            transformed = _format_intake_form_markdown(body)
            if not transformed.strip():
                skipped += 1
                continue

            if transformed.strip() == body.strip():
                skipped += 1
                continue

            meta["document_source"] = "intake_form"
            meta["content_type"] = "intake_form"
            meta["content_hash"] = compute_content_hash(transformed)
            updated = _build_markdown(meta=meta, body=transformed, has_frontmatter=has_fm)

            print(f"  {'[DRY-RUN] ' if dry_run else ''}rewrite: {object_path}")
            if not dry_run:
                storage.upload_bytes(
                    bucket=BUCKET,
                    path=object_path,
                    data=updated.encode("utf-8"),
                    content_type="text/markdown; charset=utf-8",
                    upsert=True,
                )
            changed += 1
        except Exception as e:
            errors += 1
            print(f"  ❌ error: {object_path}: {e}")

    return {
        "client_slug": client_slug,
        "scanned": scanned,
        "changed": changed,
        "skipped": skipped,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reformat intake form markdown already in Supabase Storage")
    parser.add_argument("--client", type=str, help="Single client slug to process")
    parser.add_argument("--all", action="store_true", help="Process all clients found in storage")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--reembed", action="store_true", help="Re-run upsert_to_pinecone.py for changed clients")
    parser.add_argument("--limit", type=int, default=None, help="Limit client count when using --all")
    args = parser.parse_args()

    if not args.client and not args.all:
        parser.error("Specify --client <slug> or --all")

    storage = _get_storage_client()
    if args.client:
        slugs = [args.client.strip()]
    else:
        slugs = _list_client_slugs(storage)
        if args.limit is not None:
            slugs = slugs[: max(0, int(args.limit))]

    print(f"Processing {len(slugs)} client(s) in bucket '{BUCKET}'")
    changed_clients: List[str] = []
    results: List[Dict[str, Any]] = []

    for slug in slugs:
        print(f"\n=== {slug} ===")
        res = reformat_client(storage=storage, client_slug=slug, dry_run=bool(args.dry_run))
        results.append(res)
        print(f"scanned={res['scanned']} changed={res['changed']} skipped={res['skipped']} errors={res['errors']}")
        if int(res.get("changed") or 0) > 0:
            changed_clients.append(slug)

    if args.reembed and not args.dry_run:
        for slug in changed_clients:
            code = _run_reembed_for_client(slug)
            if code != 0:
                print(f"❌ Re-embed failed for {slug} (exit={code})")

    total_changed = sum(int(r.get("changed") or 0) for r in results)
    total_errors = sum(int(r.get("errors") or 0) for r in results)
    print("\n=== SUMMARY ===")
    print(f"clients={len(results)} changed_files={total_changed} errors={total_errors}")


if __name__ == "__main__":
    main()
