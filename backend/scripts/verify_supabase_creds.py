#!/usr/bin/env python3
"""
Verify Supabase credentials for:
  - "AGENT" key: SUPABASE_AGENT_URL + SUPABASE_AGENT_KEY (usually anon/publishable JWT)
  - "STORAGE admin" key: SUPABASE_SERVICE_ROLE_KEY (optional, recommended for bucket ops)

This script performs *non-destructive* checks by default:
  - list buckets (agent key)
  - upload a tiny object into the existing 'client-data-sources' bucket (agent key)
  - list objects under a temp prefix (agent key)

If SUPABASE_SERVICE_ROLE_KEY is present, it additionally performs an admin check:
  - create a temporary bucket, then delete it

Usage (repo root, venv active):
  backend/venv/bin/python backend/scripts/verify_supabase_creds.py
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Add backend/ to path
import sys

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.clients.supabase_agent_storage_client import SupabaseAgentStorageClient  # noqa: E402
from app.clients.supabase_storage_client import SupabaseStorageClient  # noqa: E402
from app.config import get_settings  # noqa: E402


def _mask(s: str, keep: int = 6) -> str:
    if not s:
        return ""
    if len(s) <= keep * 2:
        return "*" * len(s)
    return f"{s[:keep]}…{s[-keep:]}"


def _decode_jwt_payload(jwt: str) -> Optional[Dict[str, Any]]:
    token = (jwt or "").strip()
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def main() -> int:
    # Load backend/.env if present
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    settings = get_settings()
    agent_url = str(settings.supabase_agent_url or "").rstrip("/")
    agent_key = (settings.supabase_agent_key or "").strip()
    service_role = (settings.supabase_service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

    print("=== Supabase credential verification ===")
    print(f"- SUPABASE_AGENT_URL: {agent_url or '(missing)'}")
    print(f"- SUPABASE_AGENT_KEY: {_mask(agent_key)}")
    print(f"- SUPABASE_SERVICE_ROLE_KEY: {_mask(service_role)}")

    if not agent_url or not agent_key:
        print("\nFAIL: SUPABASE_AGENT_URL and SUPABASE_AGENT_KEY must be set.")
        return 1

    payload = _decode_jwt_payload(agent_key)
    if payload:
        print("\nAGENT key (decoded payload):")
        print(f"- ref: {payload.get('ref')!r}")
        print(f"- role: {payload.get('role')!r}")
        print(f"- iss: {payload.get('iss')!r}")

    # 1) Storage API with agent key (read)
    print("\n[1] Storage API: list buckets (agent key)")
    try:
        agent_storage = SupabaseAgentStorageClient()
        buckets = agent_storage.list_buckets()
        print(f"OK: list_buckets() returned {len(buckets)} buckets")
    except Exception as e:
        print(f"FAIL: list_buckets() error: {e}")

    # 2) Storage API with agent key (write into existing bucket)
    bucket_name = "client-data-sources"
    tmp_prefix = f"__verify/{int(time.time())}"
    tmp_path = f"{tmp_prefix}/hello.txt"
    print(f"\n[2] Storage API: upload tiny object to '{bucket_name}' at '{tmp_path}' (agent key)")
    try:
        res = agent_storage.upload_bytes(
            bucket=bucket_name,
            path=tmp_path,
            data=b"hello",
            content_type="text/plain; charset=utf-8",
            upsert=True,
        )
        print(f"OK: uploaded -> {res.key}")
    except Exception as e:
        print(f"FAIL: upload error: {e}")

    print(f"\n[3] Storage API: list objects under '{tmp_prefix}/' (agent key)")
    try:
        # The old client implementation may be wrong about response shape; handle both.
        objs = agent_storage.list_objects(bucket=bucket_name, prefix=f"{tmp_prefix}/", limit=1000, offset=0)
        if isinstance(objs, list):
            print(f"OK: list_objects returned {len(objs)} items")
        else:
            print(f"WARN: list_objects returned non-list: {type(objs)}")
    except Exception as e:
        print(f"FAIL: list_objects error: {e}")

    # 4) Admin storage verification (service role): create + delete temp bucket
    if service_role:
        print("\n[4] Storage admin: create + delete temp bucket (service role key)")
        try:
            admin = SupabaseStorageClient(project_url=agent_url, service_role_key=service_role)
            tmp_bucket = f"__verify-bucket-{int(time.time())}"
            admin.create_bucket(tmp_bucket, public=False)
            print(f"OK: created temp bucket {tmp_bucket}")
            # Deleting requires empty bucket; it is empty.
            admin.delete_bucket(tmp_bucket)
            print(f"OK: deleted temp bucket {tmp_bucket}")
        except Exception as e:
            print(f"FAIL: storage admin check error: {e}")
    else:
        print("\n[4] Storage admin: skipped (SUPABASE_SERVICE_ROLE_KEY not set)")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


