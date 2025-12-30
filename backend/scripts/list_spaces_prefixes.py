#!/usr/bin/env python3
"""
List "folder" prefixes in a DigitalOcean Spaces bucket using S3 delimiter listing.

Why:
- Spaces has no real folders; keys use "/" prefixes.
- When you don't know the correct prefix layout (e.g., client-slug/ vs clients/client-slug/),
  delimiter listing quickly shows the top-level prefixes.

Usage:
  backend/venv/bin/python backend/scripts/list_spaces_prefixes.py \
    --bucket mintleads-clients-kb \
    --region tor1 \
    --prefix "" \
    --depth 1 \
    --limit 200

  # List subfolders under a known prefix:
  backend/venv/bin/python backend/scripts/list_spaces_prefixes.py \
    --bucket mintleads-clients-kb \
    --region tor1 \
    --prefix clients/ \
    --depth 2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3

# Add backend dir for imports when run from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.config import get_settings  # noqa: E402


def _spaces_client(region: str):
    s = get_settings()
    if not s.digitalocean_spaces_key or not s.digitalocean_spaces_secret:
        raise SystemExit("DIGITALOCEAN_SPACES_KEY/SECRET not configured (backend/.env)")
    endpoint = f"https://{region}.digitaloceanspaces.com"
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=endpoint,
        aws_access_key_id=s.digitalocean_spaces_key,
        aws_secret_access_key=s.digitalocean_spaces_secret,
    )


def list_prefixes(bucket: str, prefix: str, region: str, max_keys: int) -> List[str]:
    """
    Returns immediate child prefixes under `prefix` using Delimiter='/'.
    """
    s3 = _spaces_client(region)
    token: Optional[str] = None
    out: List[str] = []
    while True:
        kwargs: Dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": prefix,
            "Delimiter": "/",
            "MaxKeys": max_keys,
        }
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for p in resp.get("CommonPrefixes", []) or []:
            cp = p.get("Prefix")
            if cp:
                out.append(cp)
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    # dedupe while preserving order
    seen = set()
    uniq: List[str] = []
    for p in out:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq


def main() -> int:
    parser = argparse.ArgumentParser(description="List Spaces key prefixes (S3 delimiter listing).")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", default="tor1")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--depth", type=int, default=1, help="How many levels deep to expand prefixes.")
    parser.add_argument("--limit", type=int, default=200, help="Max keys per page for listing.")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of plain text.")
    args = parser.parse_args()

    bucket = args.bucket
    region = args.region
    root = args.prefix.lstrip("/")
    depth = max(1, int(args.depth))
    limit = max(1, int(args.limit))

    levels: List[List[str]] = []
    current: List[str] = [root]
    for _ in range(depth):
        next_level: List[str] = []
        for p in current:
            next_level.extend(list_prefixes(bucket=bucket, prefix=p, region=region, max_keys=limit))
        levels.append(next_level)
        current = next_level

    if args.json:
        print(json.dumps({"bucket": bucket, "region": region, "root": root, "levels": levels}, indent=2))
        return 0

    for i, lvl in enumerate(levels, start=1):
        print(f"\nLevel {i} prefixes under '{root}':")
        if not lvl:
            print("  (none)")
            continue
        for p in lvl:
            print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


