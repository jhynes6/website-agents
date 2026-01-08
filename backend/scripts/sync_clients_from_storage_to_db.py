#!/usr/bin/env python3
"""
Backfill/Sync `public.clients` from Supabase Storage folders.

Reads:
  - bucket: client-data-sources
  - per-client metadata:
      - {clientSlug}/supabase_storage_metadata.json (preferred)
      - {clientSlug}/metadata.json (fallback)
  - intake_form_url (best-effort):
      - scan {clientSlug}/intake_form/*.md and read YAML header url

Usage (repo root, venv active):
  backend/venv/bin/python backend/scripts/sync_clients_from_storage_to_db.py --all
  backend/venv/bin/python backend/scripts/sync_clients_from_storage_to_db.py --client mintleads
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Ensure backend/ is on path when running from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

import yaml  # type: ignore[import-not-found]  # noqa: E402

from app.clients.supabase_agents_db_client import SupabaseAgentsDbClient  # noqa: E402
from app.clients.supabase_storage_client import SupabaseStorageClient  # noqa: E402


BUCKET = "client-data-sources"


def _client_domain_from_website_url(website_url: Optional[str], fallback: str) -> str:
    u = (website_url or "").strip()
    if not u:
        return fallback
    if "://" not in u:
        u = "https://" + u
    try:
        p = urlparse(u)
        dom = (p.netloc or "").split("@")[-1].split(":")[0].lower().replace("www.", "").strip()
        return dom or fallback
    except Exception:
        return fallback


def _best_effort_intake_form_url(storage: SupabaseStorageClient, client_slug: str) -> Optional[str]:
    prefix = f"{client_slug}/intake_form/"
    items = storage.list_objects(BUCKET, prefix=prefix, limit=1000, offset=0, sort_by={"column": "name", "order": "asc"})
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("metadata") is None:
            continue
        name = str(it.get("name") or "")
        if not name.endswith(".md") or name.endswith("/.keep"):
            continue
        full = name if name.startswith(prefix) else f"{prefix}{name.lstrip('/')}"
        raw = storage.download_bytes(BUCKET, full).decode("utf-8", errors="ignore")
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                meta = yaml.safe_load(parts[1]) or {}
                if isinstance(meta, dict):
                    url = str(meta.get("url") or "").strip()
                    if url:
                        return url
    return None


def _list_client_slugs(storage: SupabaseStorageClient) -> List[str]:
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


def _load_client_storage_metadata(storage: SupabaseStorageClient, slug: str) -> Dict[str, Any]:
    for key in (f"{slug}/supabase_storage_metadata.json", f"{slug}/metadata.json"):
        try:
            data = storage.download_json(BUCKET, key)
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", type=str, default=None)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    storage = SupabaseStorageClient()
    db = SupabaseAgentsDbClient()

    if not args.client and not args.all:
        raise SystemExit("Provide --client <slug> or --all")

    slugs = [args.client] if args.client else _list_client_slugs(storage)

    for slug in slugs:
        meta = _load_client_storage_metadata(storage, slug)
        website_url = str(meta.get("website_url") or meta.get("website") or "").strip() or None
        drive_url = str(meta.get("drive_url") or meta.get("drive_folder_url") or "").strip() or None
        client_name = str((meta.get("metadata") or {}).get("title") or "").strip() or None
        domain = _client_domain_from_website_url(website_url, fallback=slug)
        website_field = f"https://{domain}" if domain else None
        intake_url = _best_effort_intake_form_url(storage, slug)

        row = await db.upsert_client(
            client_slug=slug,
            client_domain=domain or slug,
            client_name=client_name,
            website=website_field,
            drive_folder_url=drive_url,
            intake_form_url=intake_url,
        )
        print(json.dumps({"client_slug": slug, "upserted": True, "row": row}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(__import__("asyncio").run(main()))


