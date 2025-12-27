#!/usr/bin/env python3
"""
Sync Redis index metadata from Upstash Search indexes.

For each search index:
  - Pull documents (up to limit per index; configurable)
  - Derive title/description metadata from the first doc
  - Count pages and document_source buckets
  - Write Redis key firestarter:index:{slug}
  - Refresh firestarter:indexes list

Counts captured:
  - website_pages: document_source in {"website", "website_pages"}
  - intake_form: document_source == "intake_form"
  - client_materials: document_source == "client_materials"
  - unknown: everything else / missing
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

from upstash_redis import Redis
from upstash_search import Search

ROOT = Path(__file__).resolve().parents[1]


def load_env() -> None:
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
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception as exc:  # noqa: BLE001
            print(f"[sync] Skipping env file {path}: {exc}")


def count_doc_sources(docs: List) -> Dict[str, int]:
    counts = {
        "website_pages": 0,
        "intake_form": 0,
        "client_materials": 0,
        "unknown": 0,
    }
    for doc in docs:
        meta = getattr(doc, "metadata", None) or {}
        src = (meta.get("document_source") or "").lower()
        if src in {"website", "website_pages"}:
            counts["website_pages"] += 1
        elif src == "intake_form":
            counts["intake_form"] += 1
        elif src == "client_materials":
            counts["client_materials"] += 1
        else:
            counts["unknown"] += 1
    return counts


def _pick_homepage(idx, limit: int = 5) -> List:
    """Try several filters to get a homepage doc."""
    candidates = [
        '@metadata.content_type = "home page"',
        '@metadata.content_type = "homepage"',
        '@metadata.content_type = "home"',
    ]
    for filt in candidates:
        try:
            res = idx.search(query="*", limit=limit, filter=filt)
            if res:
                return res
        except Exception:
            continue
    # Last resort: try to get any website doc
    try:
        res = idx.search(query="*", limit=limit, filter='@metadata.document_source = "website"')
        if res:
            return res
    except Exception:
        pass
    return []


def derive_meta_sample(docs: List) -> Tuple[str, str, str, str, str]:
    url = title = desc = og = favicon = None
    for doc in docs:
        meta = getattr(doc, "metadata", None) or {}
        url = meta.get("url") or meta.get("sourceURL") or url
        title = meta.get("title") or meta.get("pageTitle") or title
        desc = meta.get("description") or meta.get("ogDescription") or desc
        og = meta.get("ogImage") or meta.get("og:image") or og
        favicon = meta.get("favicon") or favicon
        if url and title and desc and (og or favicon):
            break
    return url, title, desc, og, favicon


def _fetch_docs_with_paging(idx, limit: int) -> list:
    """
    Fetch documents with paging when provider enforces a read cap.
    If the provider throws a hard 100-doc limit, fall back to 100 max.
    """
    hard_cap = 100
    page_size = min(limit, hard_cap)
    docs: list = []
    cursor = None
    fetched = 0

    while fetched < limit:
        try:
            res = idx.search(query="*", limit=page_size, cursor=cursor)  # type: ignore[arg-type]
        except Exception as exc:
            # If the service refuses >100 or cursor, retry once with 100 and no cursor
            if "max allowed read limit" in str(exc).lower() or cursor is not None:
                try:
                    return idx.search(query="*", limit=hard_cap)
                except Exception:
                    return docs
            # No paging support; single call
            if cursor is None:
                return idx.search(query="*", limit=page_size)
            break

        if not res:
            break

        next_cursor = None
        docs_batch = res
        if isinstance(res, tuple) and len(res) == 2:
            docs_batch, next_cursor = res
        elif isinstance(res, dict) and "results" in res:
            docs_batch = res.get("results") or []
            next_cursor = res.get("cursor")

        docs.extend(docs_batch)
        fetched += len(docs_batch)
        if not next_cursor or len(docs_batch) < page_size:
            break
        cursor = next_cursor

    return docs[:limit]


def main() -> None:
    load_env()
    search = Search(url=os.environ["UPSTASH_SEARCH_REST_URL"], token=os.environ["UPSTASH_SEARCH_REST_TOKEN"])
    redis = Redis(url=os.environ["UPSTASH_REDIS_REST_URL"], token=os.environ["UPSTASH_REDIS_REST_TOKEN"])

    indexes = search.list_indexes()
    print(f"[sync] Found {len(indexes)} search indexes")

    all_index_meta = []
    limit_per_index = int(os.environ.get("SYNC_SEARCH_LIMIT", "500"))
    # Respect known per-call caps
    if limit_per_index > 500:
        limit_per_index = 500

    for slug in indexes:
        try:
            idx = search.index(slug)
            docs = _fetch_docs_with_paging(idx, limit_per_index)
            counts = count_doc_sources(docs)
            homepage_docs = _pick_homepage(idx, limit=5)
            meta_source = homepage_docs if homepage_docs else docs
            url, title, desc, og, favicon = derive_meta_sample(meta_source)

            index_metadata = {
                "url": url,
                "namespace": slug,
                "index": slug,
                "pagesCrawled": len(docs),
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "clientSlug": slug,
                "documentSourceCounts": counts,
                "metadata": {
                    "title": title,
                    "description": desc,
                    "favicon": favicon,
                    "ogImage": og,
                    "indexName": slug,
                },
            }

            key = f"firestarter:index:{slug}"
            redis.set(key, index_metadata)
            all_index_meta.append(index_metadata)
            print(f"[sync] updated {key} docs={len(docs)} counts={counts}")
        except Exception as exc:  # noqa: BLE001
            print(f"[sync] failed for {slug}: {exc}")

    # refresh list
    redis.set("firestarter:indexes", all_index_meta)
    print(f"[sync] refreshed firestarter:indexes with {len(all_index_meta)} entries")


if __name__ == "__main__":
    main()
