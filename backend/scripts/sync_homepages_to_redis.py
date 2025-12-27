#!/usr/bin/env python3
"""
Sync Redis index metadata from Upstash Search using homepage docs.

For each search index:
  - Try to fetch homepage docs via metadata filters:
      @metadata.content_type in ["home page", "homepage", "home"]
      fallback: @metadata.document_source = "website"
      fallback: first N docs
  - Derive url/title/description/favicon/ogImage from the homepage doc if present
  - Count document_source buckets across the fetched docs
  - Write Redis key firestarter:index:{slug}
  - Refresh firestarter:indexes list

Env:
  UPSTASH_SEARCH_REST_URL, UPSTASH_SEARCH_REST_TOKEN
  UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
  SYNC_SEARCH_LIMIT (optional, default 200)
"""

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
            print(f"[sync-home] Skipping env file {path}: {exc}")


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


def derive_meta(doc) -> Tuple[str, str, str, str, str]:
    meta = getattr(doc, "metadata", None) or {}
    url = meta.get("url") or meta.get("sourceURL")
    title = meta.get("title") or meta.get("pageTitle")
    desc = meta.get("description") or meta.get("ogDescription")
    og = meta.get("ogImage") or meta.get("og:image")
    favicon = meta.get("favicon")
    return url, title, desc, og, favicon


def pick_homepage(idx, limit: int, fallback_docs: List) -> Dict:
    filters = [
        '@metadata.content_type = "home page"',
        '@metadata.content_type = "homepage"',
        '@metadata.content_type = "home"',
        '@metadata.document_source = "website"',
    ]
    for filt in filters:
        try:
            res = idx.search(query="*", limit=limit, filter=filt)
            if res:
                return res[0]
        except Exception:
            continue
    return fallback_docs[0] if fallback_docs else {}


def fetch_docs(idx, limit: int) -> List:
    docs: List = []
    page_size = min(limit, 100)
    cursor = None
    fetched = 0
    while fetched < limit:
        try:
            res = idx.search(query="*", limit=page_size, cursor=cursor)  # type: ignore[arg-type]
        except Exception:
            # fallback single call
            if cursor is None:
                return idx.search(query="*", limit=page_size)
            break
        if not res:
            break
        next_cursor = None
        batch = res
        if isinstance(res, tuple) and len(res) == 2:
            batch, next_cursor = res
        elif isinstance(res, dict) and "results" in res:
            batch = res.get("results") or []
            next_cursor = res.get("cursor")
        docs.extend(batch)
        fetched += len(batch)
        if not next_cursor or len(batch) < page_size:
            break
        cursor = next_cursor
    return docs[:limit]


def main() -> None:
    load_env()
    search = Search(url=os.environ["UPSTASH_SEARCH_REST_URL"], token=os.environ["UPSTASH_SEARCH_REST_TOKEN"])
    redis = Redis(url=os.environ["UPSTASH_REDIS_REST_URL"], token=os.environ["UPSTASH_REDIS_REST_TOKEN"])

    indexes = search.list_indexes()
    print(f"[sync-home] Found {len(indexes)} search indexes")

    all_index_meta = []
    limit_per_index = int(os.environ.get("SYNC_SEARCH_LIMIT", "200"))
    if limit_per_index > 500:
        limit_per_index = 500

    for slug in indexes:
        try:
            idx = search.index(slug)
            docs = fetch_docs(idx, limit_per_index)
            counts = count_doc_sources(docs)
            homepage_doc = pick_homepage(idx, limit=5, fallback_docs=docs)
            url, title, desc, og, favicon = derive_meta(homepage_doc) if homepage_doc else (None, None, None, None, None)

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
            print(f"[sync-home] updated {key} docs={len(docs)}")
        except Exception as exc:  # noqa: BLE001
            print(f"[sync-home] failed for {slug}: {exc}")

    redis.set("firestarter:indexes", all_index_meta)
    print(f"[sync-home] refreshed firestarter:indexes with {len(all_index_meta)} entries")


if __name__ == "__main__":
    main()
