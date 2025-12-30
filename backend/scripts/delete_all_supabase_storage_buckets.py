"""
Delete ALL Supabase Storage buckets in the configured project.

SAFETY:
- Dry-run by default.
- Requires --yes to actually delete anything.
- Uses the Storage API (NOT SQL), per Supabase guidance.

Env required (server-side):
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY

Usage:
  python backend/scripts/delete_all_supabase_storage_buckets.py
  python backend/scripts/delete_all_supabase_storage_buckets.py --yes
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

# Load environment variables
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)


def _bucket_id(b: Dict[str, Any]) -> str:
    return str(b.get("id") or b.get("name") or "").strip()

def _resolve_env(*names: str) -> str:
    for n in names:
        v = os.getenv(n)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Delete ALL Supabase Storage buckets (dangerous).")
    parser.add_argument("--yes", action="store_true", help="Actually perform deletions (otherwise dry-run).")
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=1800,
        help="Max seconds to wait overall for deletes (default: 1800).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Delete object paths in batches of this size (default: 500).",
    )
    parser.add_argument(
        "--supabase-url",
        default="",
        help="Supabase project URL. If omitted, uses SUPABASE_URL or BISON_SUPABASE_PROJECT_URL.",
    )
    parser.add_argument(
        "--service-role-key",
        default="",
        help="Supabase service-role key. If omitted, uses SUPABASE_SERVICE_ROLE_KEY or BISON_SUPABASE_SERVICE_ROLE_KEY.",
    )
    args = parser.parse_args(argv)

    from app.clients.supabase_agent_storage_client import SupabaseAgentStorageClient

    project_url = (args.supabase_url or "").strip() or _resolve_env("SUPABASE_AGENT_URL", "SUPABASE_URL", "BISON_SUPABASE_PROJECT_URL")
    service_role_key = (args.service_role_key or "").strip() or _resolve_env(
        "SUPABASE_AGENT_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "BISON_SUPABASE_SERVICE_ROLE_KEY",
    )

    if not project_url or not service_role_key:
        print("Missing required credentials for Storage admin operations.")
        print("- Need a Supabase project URL and API key.")
        print("- Provide via flags: --supabase-url ... --service-role-key ...")
        print("- Or set env vars: SUPABASE_AGENT_URL and SUPABASE_AGENT_KEY")
        print("  (also supported: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)")
        return 2

    client = SupabaseAgentStorageClient(project_url=project_url, api_key=service_role_key)
    buckets = client.list_buckets()
    ids = [i for i in (_bucket_id(b) for b in buckets) if i]

    if not ids:
        print("No buckets found.")
        return 0

    print("Buckets found:")
    for bid in ids:
        print(f"- {bid}")

    if not args.yes:
        print("\nDry-run: no changes made. Re-run with --yes to delete ALL buckets above.")
        return 0

    # Supabase emptyBucket is async ("queued; may take up to an hour").
    # Strategy:
    # - queue empty for all buckets first
    # - then poll delete until each bucket becomes deletable (or timeout)
    print("\nDeleting ALL buckets by explicitly deleting objects, then the bucket...")
    deleted: List[str] = []
    failed: List[str] = []

    batch_size = max(1, int(args.batch_size))
    deadline = time.time() + max(0, int(args.wait_seconds))

    def time_left() -> float:
        return deadline - time.time()

    for bid in ids:
        if time_left() <= 0:
            print(f"!! Timeout reached before processing bucket '{bid}'.")
            failed.append(bid)
            continue

        print(f"\n==> Processing bucket: {bid}")

        def delete_prefix_objects(prefix: str) -> int:
            """
            Delete all objects under a given prefix.

            We re-query from offset=0 after each batch so deletions don't cause
            us to skip remaining objects (Supabase list uses offset pagination).
            """
            total = 0
            while time_left() > 0:
                items = client.list_objects(bid, prefix=prefix, limit=batch_size, offset=0)
                if not items:
                    break
                paths = [str(obj.get("name") or "") for obj in items if obj.get("name")]
                if not paths:
                    break
                for i in range(0, len(paths), batch_size):
                    chunk = paths[i : i + batch_size]
                    client.delete_objects(bid, chunk)
                    total += len(chunk)
            return total

        # 1) Enumerate folders (top-level prefixes) without deleting to avoid pagination gaps
        top_level_prefixes = set()
        root_level_objects: List[str] = []
        offset = 0
        try:
            while time_left() > 0:
                items = client.list_objects(bid, prefix="", limit=batch_size, offset=offset)
                if not items:
                    break
                for obj in items:
                    name = str(obj.get("name") or "").strip()
                    if not name:
                        continue
                    if "/" in name:
                        top_level_prefixes.add(name.split("/", 1)[0])
                    else:
                        root_level_objects.append(name)
                if len(items) < batch_size:
                    break
                offset += len(items)
        except Exception as exc:  # noqa: BLE001
            print(f"!! Failed listing objects in bucket '{bid}': {exc}")
            failed.append(bid)
            continue

        # 2) Delete root-level objects first (no folder/prefix)
        try:
            if root_level_objects:
                print(f"   Deleting {len(root_level_objects)} root-level objects...")
                for i in range(0, len(root_level_objects), batch_size):
                    chunk = root_level_objects[i : i + batch_size]
                    client.delete_objects(bid, chunk)
        except Exception as exc:  # noqa: BLE001
            print(f"!! Failed deleting root-level objects in bucket '{bid}': {exc}")
            failed.append(bid)
            continue

        # 3) Delete each folder (top-level prefix) individually
        try:
            for pref in sorted(top_level_prefixes):
                pref_path = f"{pref.rstrip('/')}/"
                deleted_in_pref = delete_prefix_objects(pref_path)
                print(f"   Deleted {deleted_in_pref} objects from folder '{pref_path}'")
        except Exception as exc:  # noqa: BLE001
            print(f"!! Failed deleting folders in bucket '{bid}': {exc}")
            failed.append(bid)
            continue

        # 4) Safety: if anything still remains, clear it with a final sweep
        try:
            leftover = delete_prefix_objects("")
            if leftover:
                print(f"   Deleted {leftover} remaining objects after folder sweep.")
        except Exception as exc:  # noqa: BLE001
            print(f"!! Failed final cleanup in bucket '{bid}': {exc}")
            failed.append(bid)
            continue

        # 2) Attempt bucket delete
        try:
            client.delete_bucket(bid)
            print(f"✅ Deleted bucket: {bid}")
            deleted.append(bid)
        except Exception as exc:  # noqa: BLE001
            print(f"!! Failed deleting bucket '{bid}': {exc}")
            failed.append(bid)

    print("\nSummary:")
    print(f"- Deleted: {len(deleted)}")
    if deleted:
        for bid in deleted:
            print(f"  - {bid}")
    print(f"- Failed: {len(failed)}")
    if failed:
        for bid in failed:
            print(f"  - {bid}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


