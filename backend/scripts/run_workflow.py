"""
CLI entrypoint to run the main crawl workflow locally.

Usage:
  python scripts/run_workflow.py --url https://example.com --client-slug myslug

Defaults:
  - mode: crawl
  - max pages: 500
  - max depth: 3
"""

import argparse
import asyncio
import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# Ensure the app package is importable when running from repo root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_payload(
    url: Optional[str],
    client_slug: Optional[str],
    max_pages: int,
    max_depth: int,
    drive_folder: Optional[str],
    skip_redis: bool,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "url": url,
        "index": client_slug or None,
        "limit": max_pages,
        "maxDepth": max_depth,
        "clientSlug": client_slug,
    }
    if drive_folder:
        payload["clientDriveFolder"] = drive_folder
    if skip_redis:
        payload["skipRedisSave"] = True
    return payload


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    """
    Load rows from a CSV with columns:
      - `client-slug` (required)
      - either `website` or `drive-id`
    Column aliases accepted: client_slug, drive_id.
    Returns a list of dicts with normalized keys.
    """
    rows: List[Dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        if not reader.fieldnames:
            raise ValueError("CSV has no headers. Expected headers: client-slug + website or drive-id")

        for raw in reader:
            normalized = {
                k.strip().lower().lstrip("\ufeff"): (v.strip() if isinstance(v, str) else "")
                for k, v in raw.items()
            }
            website = normalized.get("website") or ""
            drive_id = normalized.get("drive-id") or normalized.get("drive_id") or ""
            client_slug = normalized.get("client-slug") or normalized.get("client_slug")
            if not client_slug:
                print(f"[CLI] Skipping row with missing client-slug: {raw}")
                continue
            if not website and not drive_id:
                print(f"[CLI] Skipping row with neither website nor drive-id: {raw}")
                continue
            rows.append({"website": website or None, "drive_id": drive_id or None, "client_slug": client_slug})
    return rows


def load_env_files() -> None:
    """
    Best-effort load of env files before importing app modules (which resolve settings at import time).
    Priority: backend/.env.local -> backend/.env -> repo/.env.local -> repo/.env
    """
    candidates = [
        ROOT / ".env",
        ROOT.parent / ".env",
    ]

    for path in candidates:
        if not path.exists():
            continue
        try:
            with path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ.setdefault(key, val)
        except Exception as exc:  # noqa: BLE001
            print(f"[CLI] Skipping env file {path}: {exc}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the crawl workflow locally (CLI).")
    parser.add_argument("--url", help="Website to crawl (e.g., https://example.com)")
    parser.add_argument("--client-slug", dest="client_slug", default=None, help="Client slug / index name to use")
    parser.add_argument("--max-pages", dest="max_pages", type=int, default=500, help="Maximum pages to crawl (default: 500)")
    parser.add_argument("--max-depth", dest="max_depth", type=int, default=3, help="Maximum crawl depth (default: 3)")
    parser.add_argument("--input-file", dest="input_file", type=Path, help="CSV file with columns `website` and `client-slug` to run sequentially")
    parser.add_argument("--map", dest="use_map", action="store_true", help="Use map + scrape flow instead of crawl")
    parser.add_argument("--drive-folder-id", dest="drive_folder", default=None, help="Google Drive folder ID or URL (drive-only or combined)")
    parser.add_argument("--skip-redis", dest="skip_redis", action="store_true", help="Do not update Redis index metadata")
    args = parser.parse_args()

    if not args.url and not args.input_file and not args.drive_folder:
        parser.error("Either --url, --drive-folder-id, or --input-file is required.")
    if not args.client_slug and not args.input_file:
        parser.error("--client-slug is required (or provide it per-row via --input-file)")

    # Load environment before importing app modules that read settings
    load_env_files()

    # Import here so env is available for get_settings()
    from app.routes.create import create_chatbot, map_site, scrape_urls  # noqa: WPS433

    payloads: Sequence[Dict[str, Any]] = []

    if args.input_file:
        rows = load_csv_rows(args.input_file)
        if not rows:
            print(f"[CLI] No valid rows found in {args.input_file}")
            return
        for row in rows:
            payloads.append(
                build_payload(
                    row.get("website"),
                    row.get("client_slug"),
                    args.max_pages,
                    args.max_depth,
                    row.get("drive_id"),
                    args.skip_redis,
                )
            )
    else:
        payloads = [
            build_payload(
                args.url,
                args.client_slug,
                args.max_pages,
                args.max_depth,
                args.drive_folder,
                args.skip_redis,
            )
        ]

    for idx, payload in enumerate(payloads, start=1):
        print(f"[CLI] Starting job {idx}/{len(payloads)} with payload: {payload} (mode={'map+scrape' if args.use_map else 'crawl'})")
        try:
            if args.use_map:
                if not payload.get("url"):
                    raise RuntimeError("Map + scrape requires a URL; drive-only is not supported for --map")
                # Map first
                map_resp = await map_site({"url": payload["url"], "limit": payload["limit"]})
                links = map_resp.get("links") or []
                urls = []
                for link in links:
                    if isinstance(link, str):
                        urls.append(link)
                    elif isinstance(link, dict) and link.get("url"):
                        urls.append(link["url"])
                print(f"[CLI] Map returned {len(urls)} URLs:")
                for u in urls:
                    print(f" - {u}")
                if not urls:
                    raise RuntimeError("Map returned no URLs; aborting scrape.")

                # Scrape the mapped URLs
                scrape_payload = {
                    "urls": urls,
                    "index": payload.get("index"),
                    "clientSlug": payload.get("clientSlug"),
                }
                scrape_result = await scrape_urls(scrape_payload)
                print(f"[CLI] Workflow {idx}/{len(payloads)} complete (map+scrape):")
                print(scrape_result)
            else:
                result = await create_chatbot(payload)
                print(f"[CLI] Workflow {idx}/{len(payloads)} complete (crawl/drive):")
                docs = len(result.get("data") or [])
                print(f"[CLI] namespace={result.get('namespace')} index={result.get('index')} docs={docs} message={result.get('message')}")
        except Exception as exc:  # noqa: BLE001
            print(f"[CLI] Workflow failed for payload {payload}: {exc}")
            raise


if __name__ == "__main__":
    asyncio.run(main())

