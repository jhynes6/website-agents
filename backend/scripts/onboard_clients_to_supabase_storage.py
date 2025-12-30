"""
Onboard clients into Supabase Storage (mintleads-agents project).

Workflow:
  1) Ensure bucket exists (bucket name = client_slug)
  2) Ensure folder prefixes (website/drive/intake_form)
  3) Crawl website and upload artifacts to website/
  4) Ingest Drive folder and upload artifacts to drive/ and intake_form/

Usage (repo root, venv active):
  backend/venv/bin/python backend/scripts/onboard_clients_to_supabase_storage.py --client-slug vew-media

  # Or all clients from backend/scripts/io/_client_kb_master/clients/*.json
  backend/venv/bin/python backend/scripts/onboard_clients_to_supabase_storage.py --all
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure backend/ is on path when running from repo root
import sys

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.services.client_onboarding_storage import onboard_client_to_supabase_storage  # noqa: E402


CLIENTS_DIR = Path("backend/scripts/io/_client_kb_master/clients")


def _load_client_record(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid client record JSON: {path}")
    return data


def _candidate_client_files() -> List[Path]:
    if not CLIENTS_DIR.exists():
        raise SystemExit(f"Clients directory not found: {CLIENTS_DIR}")
    files = sorted(CLIENTS_DIR.glob("*.json"))
    # exclude master records
    files = [p for p in files if not p.name.startswith("_")]
    return files


async def _run_one(client_slug: str, *, website_limit: int, website_max_depth: Optional[int]) -> Dict[str, Any]:
    # locate file by slug
    files = _candidate_client_files()
    match = None
    for p in files:
        if p.stem == client_slug:
            match = p
            break
    if not match:
        raise SystemExit(f"Client slug not found in {CLIENTS_DIR}: {client_slug}")

    rec = _load_client_record(match)
    slug = (rec.get("client_slug") or "").strip()
    if not slug:
        raise SystemExit(f"Missing client_slug in {match}")

    result = await onboard_client_to_supabase_storage(
        client_slug=slug,
        website_url=rec.get("website_url"),
        drive_folder_url=rec.get("drive_folder_url"),
        intake_form_url=rec.get("intake_form_url"),
        website_limit=website_limit,
        website_max_depth=website_max_depth,
    )
    return {
        "client_slug": result.client_slug,
        "bucket": result.bucket,
        "ensured_bucket_created": result.ensured_bucket,
        "website": result.website,
        "drive": result.drive,
        "intake_form": result.intake_form,
    }


async def _run_all(*, website_limit: int, website_max_depth: Optional[int], limit_clients: Optional[int]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    files = _candidate_client_files()
    if limit_clients:
        files = files[: int(limit_clients)]

    for p in files:
        rec = _load_client_record(p)
        slug = (rec.get("client_slug") or "").strip()
        if not slug:
            continue
        print(f"\n=== onboarding {slug} ===")
        try:
            res = await onboard_client_to_supabase_storage(
                client_slug=slug,
                website_url=rec.get("website_url"),
                drive_folder_url=rec.get("drive_folder_url"),
                intake_form_url=rec.get("intake_form_url"),
                website_limit=website_limit,
                website_max_depth=website_max_depth,
            )
            out.append(
                {
                    "client_slug": res.client_slug,
                    "bucket": res.bucket,
                    "ensured_bucket_created": res.ensured_bucket,
                    "website": res.website,
                    "drive": res.drive,
                    "intake_form": res.intake_form,
                }
            )
        except Exception as e:  # noqa: BLE001
            out.append({"client_slug": slug, "status": "error", "error": str(e)})
            print(f"ERROR onboarding {slug}: {e}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Onboard clients into Supabase Storage.")
    parser.add_argument("--client-slug", default=None, help="Single client slug to onboard (must exist in clients dir).")
    parser.add_argument("--all", action="store_true", help="Onboard all clients from the clients dir.")
    parser.add_argument("--limit-clients", type=int, default=None, help="When using --all, stop after this many clients.")
    parser.add_argument("--website-limit", type=int, default=500, help="Max website pages to crawl.")
    parser.add_argument("--website-max-depth", type=int, default=None, help="Optional crawl max depth.")

    args = parser.parse_args()

    if not args.all and not args.client_slug:
        raise SystemExit("Pass --client-slug <slug> or --all")
    if args.all and args.client_slug:
        raise SystemExit("Use either --client-slug or --all (not both)")

    if args.client_slug:
        res = asyncio.run(_run_one(args.client_slug, website_limit=args.website_limit, website_max_depth=args.website_max_depth))
        print(json.dumps(res, indent=2))
        return 0

    results = asyncio.run(
        _run_all(website_limit=args.website_limit, website_max_depth=args.website_max_depth, limit_clients=args.limit_clients)
    )
    print("\n=== summary ===")
    print(json.dumps({"count": len(results), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


