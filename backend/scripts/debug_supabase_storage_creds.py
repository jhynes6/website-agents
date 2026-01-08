#!/usr/bin/env python3
"""
Debug Supabase Storage credentials for the Agents project.

This script:
1) Prints which Supabase env vars are set and which key the code will use.
2) Detects if the key looks like a JWT (3-part "compact JWS") vs publishable key.
3) Attempts to upload files from a local backup folder to Supabase Storage.

Example:
  backend/venv/bin/python backend/scripts/debug_supabase_storage_creds.py \
    --bucket client-data-sources \
    --client-slug mintleads \
    --local-dir data/supabase_backup/mintleads \
    --limit 5
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


# Ensure backend/ is on sys.path when running from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.config import get_settings  # noqa: E402
from app.clients.supabase_agent_storage_client import SupabaseAgentStorageClient  # noqa: E402


def _mask_secret(s: str, *, head: int = 10, tail: int = 6) -> str:
    v = (s or "").strip()
    if not v:
        return "<empty>"
    if len(v) <= head + tail:
        return v[: max(1, head)] + "…"  # avoid showing full short secrets
    return f"{v[:head]}…{v[-tail:]}"


def _looks_like_jwt(token: str) -> bool:
    t = (token or "").strip()
    parts = t.split(".")
    return len(parts) == 3 and all(p.strip() for p in parts)


def _decode_jwt_payload(token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Best-effort decode of JWT payload without signature verification (debug only).
    Returns (payload, error).
    """
    t = (token or "").strip()
    if not _looks_like_jwt(t):
        return None, "not a 3-part JWT"
    try:
        payload_b64 = t.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        raw = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else {"_raw": payload}, None
    except Exception as e:  # noqa: BLE001
        return None, f"decode error: {e}"


def _print_env_overview() -> None:
    keys = [
        "SUPABASE_AGENT_URL",
        "SUPABASE_AGENT_KEY",
        "SUPABASE_AGENT_PUBLISHABLE_KEY",
        "SUPABASE_AGENT_SERVICE_ROLE_KEY",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
    ]
    print("\n=== Env var presence (not values) ===")
    for k in keys:
        v = os.getenv(k)
        print(f"- {k}: {'SET' if v else 'unset'}")


def _print_resolved_settings() -> None:
    s = get_settings()
    print("\n=== Resolved settings (masked) ===")
    print(f"- supabase_agent_url: {str(s.supabase_agent_url or '')}")
    print(f"- supabase_agent_key: {_mask_secret(str(s.supabase_agent_key or ''))}")
    print(f"- supabase_agent_publishable_key: {_mask_secret(str(s.supabase_agent_publishable_key or ''))}")
    print(f"- supabase_agent_service_role_key: {_mask_secret(str(s.supabase_agent_service_role_key or ''))}")
    print(f"- supabase_url: {str(s.supabase_url or '')}")
    print(f"- supabase_service_role_key: {_mask_secret(str(s.supabase_service_role_key or ''))}")

    # Which key SupabaseAgentStorageClient will actually use:
    chosen = (str(s.supabase_agent_service_role_key or "").strip() or str(s.supabase_agent_key or "").strip())
    print("\n=== Auth key used by SupabaseAgentStorageClient ===")
    src = "SUPABASE_AGENT_SERVICE_ROLE_KEY" if str(s.supabase_agent_service_role_key or "").strip() else "SUPABASE_AGENT_KEY"
    print(f"- source: settings ({src})")
    if not chosen:
        print("- value: <empty>")
        return
    print(f"- masked: {_mask_secret(chosen)}")
    print(f"- length: {len(chosen)}")
    if chosen.startswith("sb_publishable_"):
        print("- format: sb_publishable_* (NOT a JWT)  <-- likely cause of 'Invalid Compact JWS'")
    else:
        print(f"- looks_like_jwt: {_looks_like_jwt(chosen)}")
        payload, err = _decode_jwt_payload(chosen)
        if payload:
            role = payload.get("role")
            iss = payload.get("iss")
            exp = payload.get("exp")
            print(f"- jwt.role: {role!r}")
            print(f"- jwt.iss: {iss!r}")
            print(f"- jwt.exp: {exp!r}")
        else:
            print(f"- jwt.decode: {err}")


def _iter_local_files(local_dir: Path) -> list[Path]:
    if not local_dir.exists():
        raise FileNotFoundError(f"Local dir not found: {local_dir}")
    files = [p for p in local_dir.rglob("*") if p.is_file()]
    # Skip hidden/system artifacts
    out: list[Path] = []
    for p in files:
        name = p.name
        if name.startswith(".") and name not in (".keep",):
            continue
        out.append(p)
    return sorted(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug Supabase Storage creds and test uploads.")
    parser.add_argument("--bucket", default="client-data-sources", help="Supabase Storage bucket id.")
    parser.add_argument("--client-slug", default="mintleads", help="Client slug prefix in Storage.")
    parser.add_argument(
        "--local-dir",
        default="data/supabase_backup/mintleads",
        help="Local directory containing files to upload (relative to repo root or absolute).",
    )
    parser.add_argument("--limit", type=int, default=10, help="Max number of files to upload (0 = all).")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without uploading.")

    args = parser.parse_args()

    repo_root = backend_dir.parent
    local_dir = Path(args.local_dir)
    if not local_dir.is_absolute():
        local_dir = (repo_root / local_dir).resolve()

    print("=" * 88)
    print("Supabase Storage credential debug")
    print("=" * 88)
    _print_env_overview()
    _print_resolved_settings()
    print("\n=== Upload test ===")
    print(f"- bucket: {args.bucket}")
    print(f"- client_slug: {args.client_slug}")
    print(f"- local_dir: {str(local_dir)}")
    print(f"- dry_run: {args.dry_run}")
    print(f"- limit: {args.limit}")

    files = _iter_local_files(local_dir)
    if args.limit and args.limit > 0:
        files = files[: args.limit]
    print(f"- files_found: {len(files)}")

    if args.dry_run:
        for p in files[: min(10, len(files))]:
            rel = p.relative_to(local_dir).as_posix()
            dest = f"{args.client_slug}/{rel}"
            print(f"  would_upload: {rel} -> {dest} ({p.stat().st_size} bytes)")
        print("\nDry-run complete.")
        return 0

    client = SupabaseAgentStorageClient()
    ok = 0
    failed = 0
    for p in files:
        rel = p.relative_to(local_dir).as_posix()
        dest = f"{args.client_slug}/{rel}"
        try:
            data = p.read_bytes()
            # Minimal content type mapping
            ct = "application/octet-stream"
            if rel.endswith(".md"):
                ct = "text/markdown; charset=utf-8"
            elif rel.endswith(".json"):
                ct = "application/json; charset=utf-8"
            elif rel.endswith(".txt"):
                ct = "text/plain; charset=utf-8"

            client.upload_bytes(bucket=args.bucket, path=dest, data=data, content_type=ct, upsert=True)
            ok += 1
            print(f"✓ uploaded {rel} -> {dest} ({len(data)} bytes)")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"✗ FAILED {rel} -> {dest}: {e}")

    print("\n=== Result ===")
    print(f"- uploaded_ok: {ok}")
    print(f"- uploaded_failed: {failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())


