#!/usr/bin/env python3
"""
Migrate Redis index metadata keys to the canonical format:
  - Single key per client: firestarter:index:{client-slug}
  - Metadata fields set to the slug for namespace/index/clientSlug
  - Index list rebuilt to match

Intended for Upstash Redis (uses REST client).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from upstash_redis import Redis

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    """Load env vars from common locations (best-effort, no override)."""
    candidates = [
        ROOT / ".env.local",
        ROOT / ".env",
        ROOT.parent / ".env.local",
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
            print(f"[migrate] Skipping env file {path}: {exc}")


def _normalize_slug(raw: str | None) -> str:
    if not raw:
        return ""
    lowered = raw.strip().lower()
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in lowered)
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-")


def _deduce_slug(meta: Dict[str, Any]) -> str:
    direct = meta.get("clientSlug") or meta.get("index") or meta.get("namespace")
    if direct:
        return _normalize_slug(str(direct))
    return ""


def _maybe_strip_timestamp(ns: str) -> str:
    if "-" in ns:
        parts = ns.rsplit("-", 1)
        if parts[1].isdigit():
            return parts[0]
    return ns


def _connect() -> Redis:
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        raise RuntimeError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN are required")
    return Redis(url=url, token=token)


def _scan_keys(redis: Redis, pattern: str) -> list[str]:
    keys: list[str] = []
    cursor = 0
    while True:
        cursor, batch = redis.scan(cursor=cursor, match=pattern, count=100)
        keys.extend(batch)
        if cursor == 0:
            break
    return keys


def main() -> None:
    _load_env()
    redis = _connect()

    keys = _scan_keys(redis, "firestarter:index:*")
    print(f"[migrate] Found {len(keys)} keys to inspect")

    chosen: Dict[str, Dict[str, Any]] = {}
    originals: Dict[str, str] = {}  # old_key -> slug

    for key in keys:
        raw = redis.get(key)
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                print(f"[migrate] Skipping non-JSON value at {key}")
                continue
        if not isinstance(raw, dict):
            print(f"[migrate] Skipping non-dict value at {key}")
            continue

        slug = _deduce_slug(raw)
        if not slug and raw.get("namespace"):
            slug = _normalize_slug(_maybe_strip_timestamp(str(raw["namespace"])))

        if not slug:
            print(f"[migrate] Skipping key {key} (no slug/namespace)")
            continue

        raw = {**raw}
        raw["clientSlug"] = slug
        raw["namespace"] = slug
        raw["index"] = slug

        # Prefer the most recently created entry if available
        def _created_at(meta: Dict[str, Any]) -> str:
            return str(meta.get("createdAt") or "")

        if slug not in chosen or _created_at(raw) > _created_at(chosen[slug]):
            chosen[slug] = raw
            originals[key] = slug

    # Write canonical keys
    for slug, meta in chosen.items():
        new_key = f"firestarter:index:{slug}"
        redis.set(new_key, meta)
        # Delete legacy keys that map to this slug but differ
        for old_key, old_slug in list(originals.items()):
            if old_slug == slug and old_key != new_key:
                redis.delete(old_key)
                originals.pop(old_key, None)
        print(f"[migrate] Upserted {new_key}")

    # Rebuild the indexes list
    index_list = list(chosen.values())
    redis.set("firestarter:indexes", index_list)
    print(f"[migrate] Rebuilt firestarter:indexes with {len(index_list)} entries")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"[migrate] Failed: {exc}", file=sys.stderr)
        sys.exit(1)
