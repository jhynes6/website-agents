#!/usr/bin/env python3
"""
Create Pinecone Assistants for every namespace in a Pinecone KB index.

In this repo, KB namespaces correspond to client slugs.

Default target:
  - index: sb-knowledge-bases (via PINECONE_KB_INDEX; defaults set in backend/app/config.py)

This script:
  1) lists namespaces in the KB index (and optionally filters by min vector count)
  2) for each namespace, runs backend/scripts/create_assistant.py logic (uploading markdown from Supabase Storage)

Usage (repo root, venv active):
  backend/venv/bin/python backend/scripts/create_assistants_for_kb_namespaces.py

  # Force recreate:
  backend/venv/bin/python backend/scripts/create_assistants_for_kb_namespaces.py --force

  # Limit to first 5 namespaces:
  backend/venv/bin/python backend/scripts/create_assistants_for_kb_namespaces.py --limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure backend/ is on path when running from repo root
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))
# Also ensure this scripts directory is importable (for create_assistant.py)
scripts_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(scripts_dir))

from pinecone import Pinecone  # noqa: E402

from app.config import get_settings  # noqa: E402
from create_assistant import create_assistant_for_client  # noqa: E402


def _extract_namespaces(stats_obj: Any) -> Dict[str, Any]:
    """
    Pinecone SDK can return either:
      - an object with `.namespaces`
      - a dict with {"namespaces": {...}}
    """
    if hasattr(stats_obj, "namespaces"):
        ns = getattr(stats_obj, "namespaces")
        return ns if isinstance(ns, dict) else {}
    if isinstance(stats_obj, dict):
        ns = stats_obj.get("namespaces")
        return ns if isinstance(ns, dict) else {}
    return {}


def _namespace_vector_count(ns_info: Any) -> int:
    if isinstance(ns_info, dict):
        return int(ns_info.get("vector_count") or 0)
    # Some SDK versions may use objects with attribute
    vc = getattr(ns_info, "vector_count", 0)
    try:
        return int(vc or 0)
    except Exception:
        return 0


def list_kb_namespaces(*, index_name: str) -> List[Tuple[str, int]]:
    settings = get_settings()
    if not settings.pinecone_api_key:
        raise SystemExit("PINECONE_API_KEY is required")

    pc = Pinecone(api_key=settings.pinecone_api_key)
    desc = pc.describe_index(index_name)
    idx = pc.Index(host=desc.host)
    stats = idx.describe_index_stats()

    namespaces = _extract_namespaces(stats)
    out: List[Tuple[str, int]] = []
    for name, info in namespaces.items():
        if not isinstance(name, str):
            continue
        out.append((name, _namespace_vector_count(info)))
    out.sort(key=lambda x: x[0])
    return out


async def main() -> int:
    parser = argparse.ArgumentParser(description="Create Pinecone Assistants for every KB namespace.")
    parser.add_argument(
        "--index",
        default=None,
        help="Pinecone KB index name (default: PINECONE_KB_INDEX / backend default).",
    )
    parser.add_argument("--min-vectors", type=int, default=1, help="Only include namespaces with at least this many vectors.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N namespaces (after filtering).")
    parser.add_argument("--force", action="store_true", help="Delete and recreate assistants if they already exist.")
    parser.add_argument("--continue-on-error", action="store_true", help="Keep going even if one namespace fails.")
    parser.add_argument("--dry-run", action="store_true", help="Only list namespaces; do not create assistants.")
    args = parser.parse_args()

    settings = get_settings()
    index_name = (args.index or settings.pinecone_kb_index_name or "").strip()
    if not index_name:
        raise SystemExit("Missing index name. Set PINECONE_KB_INDEX or pass --index.")

    namespaces = list_kb_namespaces(index_name=index_name)
    namespaces = [(n, c) for (n, c) in namespaces if c >= int(args.min_vectors)]
    if args.limit is not None:
        namespaces = namespaces[: max(0, int(args.limit))]

    print(f"KB index: {index_name}")
    print(f"Namespaces found (>= {args.min_vectors} vectors): {len(namespaces)}")

    if args.dry_run:
        for n, c in namespaces:
            print(f"- {n} ({c} vectors)")
        return 0

    ok = 0
    skipped = 0
    failed = 0

    for i, (namespace, count) in enumerate(namespaces, 1):
        print(f"\n[{i}/{len(namespaces)}] {namespace} ({count} vectors)")
        try:
            res = await create_assistant_for_client(client_slug=namespace, force_recreate=bool(args.force))
            if res.get("skipped"):
                skipped += 1
            elif res.get("success"):
                ok += 1
            else:
                failed += 1
                print(f"❌ Failed: {namespace}: {res.get('error') or res.get('reason')}")
                if not args.continue_on_error:
                    break
        except Exception as e:
            failed += 1
            print(f"❌ Exception: {namespace}: {e}")
            if not args.continue_on_error:
                break

    print("\n=== summary ===")
    print(f"ok: {ok}")
    print(f"skipped: {skipped}")
    print(f"failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))


