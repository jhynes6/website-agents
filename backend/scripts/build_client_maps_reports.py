#!/usr/bin/env python3
"""
Build Firecrawl /map reports for every client in public.clients and upload them to
Supabase Storage reports bucket under:

  {SUPABASE_REPORTS_BUCKET}/_reports/client_maps/{clientSlug}.json
  {SUPABASE_REPORTS_BUCKET}/_reports/client_maps/index.json

Usage:
  python3 backend/scripts/build_client_maps_reports.py --limit 5000
  python3 backend/scripts/build_client_maps_reports.py --limit 5000 --concurrency 3
  python3 backend/scripts/build_client_maps_reports.py --only airops

Requires:
  - FIRECRAWL_API_KEY
  - SUPABASE_AGENT_URL
  - SUPABASE_AGENT_SERVICE_ROLE_KEY (preferred)
  - SUPABASE_REPORTS_BUCKET (optional, default: mintleads-reports)
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# Ensure backend/ is on sys.path so we can import app.*
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.clients.firecrawl import firecrawl_client  # noqa: E402
from app.clients.supabase_agents_db_client import SupabaseAgentsDbClient  # noqa: E402
from app.services.client_maps_reports import upsert_client_map_report  # noqa: E402
from app.logging import log  # noqa: E402


def _website_for_row(row: Dict[str, Any]) -> Optional[str]:
    w = str(row.get("website") or "").strip()
    if w:
        return w
    dom = str(row.get("client_domain") or "").strip()
    if dom:
        return f"https://{dom}"
    return None


async def _map_one(
    *,
    row: Dict[str, Any],
    limit: int,
    sem: asyncio.Semaphore,
    reports_bucket: Optional[str],
) -> Dict[str, Any]:
    slug = str(row.get("client_slug") or "").strip()
    website = _website_for_row(row) or ""
    if not slug or not website:
        return {"client_slug": slug, "skipped": True, "reason": "missing slug or website"}

    async with sem:
        try:
            links_raw = await firecrawl_client.map_urls(website, limit=int(limit))
            links: List[str] = []
            for item in links_raw or []:
                if isinstance(item, dict):
                    u = str(item.get("url") or item.get("link") or item.get("href") or "").strip()
                else:
                    u = str(item or "").strip()
                if u:
                    links.append(u)
            out = upsert_client_map_report(
                client_slug=slug,
                website_url=website,
                links=links,
                limit_used=int(limit),
                reports_bucket=reports_bucket,
            )
            return {"client_slug": slug, "ok": True, **out}
        except Exception as e:
            log("reports.client_maps.error", {"client": slug, "website": website, "error": str(e)})
            return {"client_slug": slug, "ok": False, "error": str(e)}


async def main_async() -> int:
    p = argparse.ArgumentParser(description="Build /map reports for all clients in public.clients")
    p.add_argument("--limit", type=int, default=5000, help="Firecrawl map limit per client (default: 5000)")
    p.add_argument("--concurrency", type=int, default=3, help="Concurrent /map calls (default: 3)")
    p.add_argument("--only", type=str, default="", help="Only run for one client slug")
    p.add_argument("--reports-bucket", type=str, default="", help="Override reports bucket (default from env/config)")
    args = p.parse_args()

    db = SupabaseAgentsDbClient()
    rows = await db.list_clients_for_mapping(limit=20_000)
    only = (args.only or "").strip()
    if only:
        rows = [r for r in rows if str(r.get("client_slug") or "").strip() == only]

    reports_bucket = (args.reports_bucket or "").strip() or None

    sem = asyncio.Semaphore(max(1, int(args.concurrency)))
    tasks = [
        _map_one(row=r, limit=int(args.limit), sem=sem, reports_bucket=reports_bucket)
        for r in rows
    ]
    results = await asyncio.gather(*tasks)

    ok = sum(1 for r in results if r.get("ok"))
    failed = sum(1 for r in results if (r.get("ok") is False))
    skipped = sum(1 for r in results if r.get("skipped"))
    print(f"✅ client map reports complete: ok={ok} failed={failed} skipped={skipped} total={len(results)}")
    if failed:
        print("Some clients failed. Re-run with --only <clientSlug> to debug.")
        return 2
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())


