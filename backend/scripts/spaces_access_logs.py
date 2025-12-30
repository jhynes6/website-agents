#!/usr/bin/env python3
"""
Enable/disable/inspect DigitalOcean Spaces access logs using the S3-compatible API.

Why this exists:
- Some environments don't have AWS CLI installed, or `aws` resolves to a different Python package.
- Spaces supports S3 server access logs via PutBucketLogging/GetBucketLogging.

Docs:
- DigitalOcean Spaces access logs: https://docs.digitalocean.com/products/spaces/how-to/access-logs/

Usage:
  backend/venv/bin/python backend/scripts/spaces_access_logs.py status \
    --bucket mintleads-clients-kb

  backend/venv/bin/python backend/scripts/spaces_access_logs.py enable \
    --bucket mintleads-clients-kb \
    --target-bucket mintleads-clients-kb-logs \
    --target-prefix access-logs/mintleads-clients-kb/

  backend/venv/bin/python backend/scripts/spaces_access_logs.py disable \
    --bucket mintleads-clients-kb
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

# Add backend dir for imports when run from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.config import get_settings  # noqa: E402


COMMON_SPACES_REGIONS: List[str] = [
    # Common Spaces regions (as of 2025)
    "nyc3",
    "sfo3",
    "ams3",
    "sgp1",
    "fra1",
    "tor1",
    "blr1",
]


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


def _get_logging(s3, bucket: str) -> Dict[str, Any]:
    # For S3-compatible APIs, missing logging config typically returns {}.
    resp = s3.get_bucket_logging(Bucket=bucket)  # type: ignore[no-untyped-call]
    return resp or {}


def cmd_status(*, bucket: str, region: str) -> int:
    s3 = _spaces_client(region)
    resp = _get_logging(s3, bucket)
    enabled = bool(resp.get("LoggingEnabled"))
    print(json.dumps({"bucket": bucket, "region": region, "enabled": enabled, "logging": resp}, indent=2))
    return 0


def cmd_enable(*, bucket: str, region: str, target_bucket: str, target_prefix: str) -> int:
    if bucket == target_bucket:
        raise SystemExit("Target bucket must be different from source bucket (Spaces requirement).")
    if target_prefix and not target_prefix.endswith("/"):
        target_prefix = target_prefix + "/"

    s3 = _spaces_client(region)
    cfg = {"LoggingEnabled": {"TargetBucket": target_bucket, "TargetPrefix": target_prefix}}
    try:
        # Quick sanity checks to surface common errors early
        try:
            s3.head_bucket(Bucket=bucket)  # type: ignore[no-untyped-call]
        except ClientError as e:
            raise ClientError(e.response, "HeadBucket(source)") from e

        try:
            s3.head_bucket(Bucket=target_bucket)  # type: ignore[no-untyped-call]
        except ClientError as e:
            raise ClientError(e.response, "HeadBucket(target)") from e

        s3.put_bucket_logging(  # type: ignore[no-untyped-call]
            Bucket=bucket,
            BucketLoggingStatus=cfg,
        )
    except ClientError as e:
        err = (e.response or {}).get("Error") or {}
        code = err.get("Code") or "Unknown"
        msg = err.get("Message") or str(e)
        op = getattr(e, "operation_name", None) or "UnknownOperation"
        hints = [
            "Confirm the destination bucket exists (and is in the same Spaces region).",
            "Confirm your access key can WRITE to the destination bucket.",
            "Destination bucket must be DIFFERENT from the source bucket.",
        ]
        print(
            json.dumps(
                {
                    "ok": False,
                    "action": "enable",
                    "bucket": bucket,
                    "region": region,
                    "target_bucket": target_bucket,
                    "target_prefix": target_prefix,
                    "error": {"code": code, "message": msg},
                    "operation": op,
                    "hints": hints,
                },
                indent=2,
            )
        )
        return 2
    # Re-read to confirm
    after = _get_logging(s3, bucket)
    print(json.dumps({"bucket": bucket, "region": region, "set_to": cfg, "now": after}, indent=2))
    return 0


def cmd_disable(*, bucket: str, region: str) -> int:
    s3 = _spaces_client(region)
    # Disable by sending an empty status (matches DO docs behavior for AWS CLI).
    s3.put_bucket_logging(  # type: ignore[no-untyped-call]
        Bucket=bucket,
        BucketLoggingStatus={},
    )
    after = _get_logging(s3, bucket)
    print(json.dumps({"bucket": bucket, "region": region, "disabled": True, "now": after}, indent=2))
    return 0


def cmd_find_bucket(*, bucket: str, regions: List[str]) -> int:
    """
    Try to locate a bucket by probing common region endpoints.
    Useful because Spaces returns 404 when you query a bucket against the wrong region endpoint.
    """
    checked: List[Dict[str, Any]] = []
    for r in regions:
        s3 = _spaces_client(r)
        try:
            s3.head_bucket(Bucket=bucket)  # type: ignore[no-untyped-call]
            print(json.dumps({"found": True, "bucket": bucket, "region": r}, indent=2))
            return 0
        except ClientError as e:
            err = (e.response or {}).get("Error") or {}
            checked.append(
                {
                    "region": r,
                    "code": err.get("Code") or "Unknown",
                    "message": err.get("Message") or "Unknown",
                }
            )
            continue

    print(json.dumps({"found": False, "bucket": bucket, "checked": checked}, indent=2))
    return 2


def main() -> int:
    s = get_settings()

    parser = argparse.ArgumentParser(description="Manage DigitalOcean Spaces access logs (S3 bucket logging).")

    sub = parser.add_subparsers(dest="command", required=True)

    def _add_region_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--region",
            default=None,
            help="Spaces region (default env DIGITALOCEAN_SPACES_REGION). Example: tor1",
        )

    p_status = sub.add_parser("status", help="Show current bucket logging config.")
    p_status.add_argument("--bucket", required=True)
    _add_region_arg(p_status)

    p_enable = sub.add_parser("enable", help="Enable access logs for a bucket.")
    p_enable.add_argument("--bucket", required=True)
    p_enable.add_argument("--target-bucket", required=True)
    p_enable.add_argument("--target-prefix", default="", help="Where to write log objects in the target bucket.")
    _add_region_arg(p_enable)

    p_disable = sub.add_parser("disable", help="Disable access logs for a bucket.")
    p_disable.add_argument("--bucket", required=True)
    _add_region_arg(p_disable)

    p_find = sub.add_parser("find-bucket", help="Find which Spaces region endpoint a bucket exists in.")
    p_find.add_argument("--bucket", required=True)
    p_find.add_argument(
        "--regions",
        default=",".join(COMMON_SPACES_REGIONS),
        help=f"Comma-separated regions to try (default: {','.join(COMMON_SPACES_REGIONS)})",
    )

    args = parser.parse_args()

    if args.command == "status":
        region = (args.region or s.digitalocean_spaces_region or "tor1").strip()
        return cmd_status(bucket=args.bucket, region=region)
    if args.command == "enable":
        region = (args.region or s.digitalocean_spaces_region or "tor1").strip()
        return cmd_enable(
            bucket=args.bucket,
            region=region,
            target_bucket=args.target_bucket,
            target_prefix=args.target_prefix,
        )
    if args.command == "disable":
        region = (args.region or s.digitalocean_spaces_region or "tor1").strip()
        return cmd_disable(bucket=args.bucket, region=region)
    if args.command == "find-bucket":
        regions = [r.strip() for r in str(args.regions).split(",") if r.strip()]
        return cmd_find_bucket(bucket=args.bucket, regions=regions or COMMON_SPACES_REGIONS)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())


