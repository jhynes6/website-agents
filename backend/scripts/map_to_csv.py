#!/usr/bin/env python3
"""
Run Firecrawl /map via the MintAgent backend and write results to a CSV.

Usage:
  python backend/scripts/map_to_csv.py --url https://airops.com --out airops_map.csv --limit 5000

Notes:
  - Requires the backend running locally (default: http://127.0.0.1:8000)
  - The backend must have FIRECRAWL_API_KEY configured.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx


def _as_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x)


def main() -> int:
    p = argparse.ArgumentParser(description="Map a site with Firecrawl and save results to CSV")
    p.add_argument("--url", required=True, help="Base URL to map (e.g., https://airops.com)")
    p.add_argument("--out", required=True, help="Output CSV path (e.g., airops_map.csv)")
    p.add_argument("--limit", type=int, default=5000, help="Map limit (default: 5000)")
    p.add_argument(
        "--backend",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    args = p.parse_args()

    base = str(args.backend).rstrip("/")
    map_url = f"{base}/api/mintagent/map"

    payload = {"url": args.url, "limit": int(args.limit)}

    try:
        resp = httpx.post(map_url, json=payload, timeout=120)
    except Exception as e:
        print(f"❌ Failed to call backend map endpoint: {e}", file=sys.stderr)
        return 1

    if resp.status_code >= 400:
        print(f"❌ Backend returned {resp.status_code}: {resp.text}", file=sys.stderr)
        return 1

    data: Dict[str, Any] = resp.json()
    if not data.get("success"):
        print(f"❌ Map failed: {data}", file=sys.stderr)
        return 1

    links = data.get("links") or []
    rows: List[Dict[str, str]] = []
    for item in links:
        if isinstance(item, dict):
            u = _as_str(item.get("url") or item.get("link") or item.get("href") or "")
        else:
            u = _as_str(item)
        u = u.strip()
        if not u:
            continue
        rows.append({"url": u})

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["url"])
        w.writeheader()
        w.writerows(rows)

    print(f"✅ Wrote {len(rows)} URLs to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

