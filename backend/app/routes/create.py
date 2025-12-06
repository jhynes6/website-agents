import asyncio
import time
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from ..clients.firecrawl import firecrawl_client
from ..clients.llm import llm_client
from ..clients.redis_client import redis_client
from ..clients.upstash_search import upstash_search_client
from ..config import get_settings
from ..logging import log

router = APIRouter()


def _doc_id_from_url(raw_url: str) -> str:
    """Build a stable id from domain + path without a trailing slash."""
    parsed = urlparse(raw_url or "")
    netloc = parsed.netloc
    raw_path = parsed.path or "/"
    # Drop trailing slash unless the path is just "/"
    path = "" if raw_path == "/" else raw_path.rstrip("/")
    if netloc:
        return f"{netloc}{path}"
    # Fallback: if no netloc (e.g., already a bare path), return the path itself.
    return path


async def _categorize_page(p: Dict[str, Any]) -> tuple[str, str]:
    """Helper to categorize a page URL."""
    u = p.get("metadata", {}).get("sourceURL") or p.get("url") or ""
    if not u:
        return "", "other"
    cat = await llm_client.categorize_url(u)
    return u, cat


@router.post("/create")
async def create_chatbot(payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()
    url: Optional[str] = payload.get("url")
    limit: int = int(payload.get("limit") or settings.crawling_default_limit)
    include_paths: Optional[List[str]] = payload.get("includePaths")
    exclude_paths: Optional[List[str]] = payload.get("excludePaths")
    index_name: Optional[str] = payload.get("index")

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Namespace matches TS: hostname + timestamp
    base_namespace = url.replace("https://", "").replace("http://", "").split("/")[0].replace(".", "-")
    namespace = f"{base_namespace}-{int(time.time() * 1000)}"

    log("create.request", {"url": url, "limit": limit, "include": include_paths, "exclude": exclude_paths})

    pages, raw_status = await firecrawl_client.crawl_and_wait(url, limit, include_paths, exclude_paths)
    if not pages:
        raise HTTPException(status_code=502, detail="Crawl completed but returned no pages")

    pages_preview = [
        {
            "title": p.get("metadata", {}).get("title") or "Untitled",
            "url": p.get("metadata", {}).get("sourceURL") or p.get("url"),
            "hasContent": bool(p.get("markdown") or p.get("content")),
        }
        for p in pages[:5]
    ]
    log("create.pages.preview", {"sample": pages_preview, "total": len(pages)})

    # Run categorization in parallel
    log("create.categorize", {"pages": len(pages)})
    cats_results = await asyncio.gather(*[_categorize_page(p) for p in pages])
    url_to_category = dict(cats_results)

    documents = []
    for index, page in enumerate(pages):
        full_content = page.get("markdown") or page.get("content") or ""
        title = page.get("metadata", {}).get("title") or "Untitled"
        page_url = page.get("metadata", {}).get("sourceURL") or page.get("url") or ""
        description = page.get("metadata", {}).get("description") or page.get("metadata", {}).get("ogDescription") or ""
        content_type = url_to_category.get(page_url, "other")

        searchable_text = f"namespace:{namespace} {title} {description} {full_content}"[:1000]
        doc_id = _doc_id_from_url(page_url or url)

        documents.append(
            {
                "id": doc_id,
                "content": {
                    "text": searchable_text,
                    "url": page_url,
                    "title": title,
                },
                "metadata": {
                    "namespace": namespace,
                    "title": title,
                    "url": page_url,
                    "sourceURL": page_url,
                    "crawlDate": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "pageTitle": title,
                    "description": description,
                    "fullContent": full_content[:5000],
                    "content_type": content_type,
                    "document_source": "website",
                },
            }
        )

    if documents:
        log("create.upsert", {"index": index_name or settings.upstash_search_index, "docs": len(documents)})
        await upstash_search_client.upsert_documents(documents, index_name=index_name)

    homepage = next(
        (
            p
            for p in pages
            if (p.get("metadata", {}).get("sourceURL") or p.get("url") or "").rstrip("/")
            in {url.rstrip("/"), f"{url.rstrip('/')}/"}
        ),
        pages[0],
    )

    # Save index metadata to Redis for persistence
    try:
        index_metadata = {
            "url": url,
            "namespace": namespace,
            "pagesCrawled": len(pages),
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metadata": {
                "title": homepage.get("metadata", {}).get("title"),
                "description": homepage.get("metadata", {}).get("description")
                or homepage.get("metadata", {}).get("ogDescription"),
                "favicon": homepage.get("metadata", {}).get("favicon"),
                "ogImage": homepage.get("metadata", {}).get("ogImage")
                or homepage.get("metadata", {}).get("og:image"),
            },
        }
        redis_client.save_index(index_metadata)
        log("create.redis.saved", {"namespace": namespace})
    except Exception as e:
        log("create.redis.error", {"error": str(e)})

    return {
        "success": True,
        "namespace": namespace,
        "index": index_name or settings.upstash_search_index,
        "crawlStatus": raw_status,
        "message": f"Crawl completed successfully (limited to {limit} pages)",
        "details": {
            "url": url,
            "pagesLimit": limit,
            "pagesCrawled": len(pages),
        },
        "data": pages,
        "homepage": {
            "title": homepage.get("metadata", {}).get("title"),
            "description": homepage.get("metadata", {}).get("description")
            or homepage.get("metadata", {}).get("ogDescription"),
            "favicon": homepage.get("metadata", {}).get("favicon"),
            "ogImage": homepage.get("metadata", {}).get("ogImage")
            or homepage.get("metadata", {}).get("og:image"),
        },
    }


@router.post("/map")
async def map_site(payload: Dict[str, Any]) -> Dict[str, Any]:
    url: Optional[str] = payload.get("url")
    limit: int = int(payload.get("limit") or 500)
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    try:
        links = await firecrawl_client.map_urls(url, limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Map failed: {exc}") from exc
    return {"success": True, "links": links}


@router.post("/scrape")
async def scrape_urls(payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()
    urls: List[str] = payload.get("urls") or []
    if not urls:
        raise HTTPException(status_code=400, detail="urls array is required")
    namespace: Optional[str] = payload.get("namespace")
    index_name: Optional[str] = payload.get("index")
    if not namespace:
        base_namespace = urls[0].replace("https://", "").replace("http://", "").split("/")[0].replace(".", "-")
        namespace = f"{base_namespace}-{int(time.time() * 1000)}"

    pages: List[Dict[str, Any]] = []
    for target in urls:
        result = firecrawl_client.scrape_url(target)
        data = result.get("data") if isinstance(result, dict) else None
        if data:
            data["url"] = target
            pages.append(data)

    if not pages:
        raise HTTPException(status_code=502, detail="Scrape returned no pages")

    # Run categorization in parallel
    log("scrape.categorize", {"pages": len(pages)})
    cats_results = await asyncio.gather(*[_categorize_page(p) for p in pages])
    url_to_category = dict(cats_results)

    documents = []
    for index, page in enumerate(pages):
        full_content = page.get("markdown") or page.get("content") or ""
        metadata = page.get("metadata", {}) or {}
        title = metadata.get("title") or "Untitled"
        page_url = metadata.get("sourceURL") or metadata.get("url") or page.get("url") or ""
        description = metadata.get("description") or metadata.get("ogDescription") or ""
        content_type = url_to_category.get(page_url, "other")

        searchable_text = f"namespace:{namespace} {title} {description} {full_content}"[:1000]
        doc_id = _doc_id_from_url(page_url or target)

        documents.append(
            {
                "id": doc_id,
                "content": {
                    "text": searchable_text,
                    "url": page_url,
                    "title": title,
                },
                "metadata": {
                    "namespace": namespace,
                    "title": title,
                    "url": page_url,
                    "sourceURL": page_url,
                    "crawlDate": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "pageTitle": title,
                    "description": description,
                    "fullContent": full_content[:5000],
                    "content_type": content_type,
                    "document_source": "website",
                },
            }
        )

    log("scrape.upsert", {"index": index_name or settings.upstash_search_index, "docs": len(documents)})
    await upstash_search_client.upsert_documents(documents, index_name=index_name)

    homepage = pages[0]
    
    # Save index metadata to Redis for persistence
    try:
        index_metadata = {
            "url": urls[0] if urls else "",
            "namespace": namespace,
            "pagesCrawled": len(pages),
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metadata": {
                "title": homepage.get("metadata", {}).get("title"),
                "description": homepage.get("metadata", {}).get("description")
                or homepage.get("metadata", {}).get("ogDescription"),
                "favicon": homepage.get("metadata", {}).get("favicon"),
                "ogImage": homepage.get("metadata", {}).get("ogImage")
                or homepage.get("metadata", {}).get("og:image"),
            },
        }
        redis_client.save_index(index_metadata)
        log("scrape.redis.saved", {"namespace": namespace})
    except Exception as e:
        log("scrape.redis.error", {"error": str(e)})
    
    return {
        "success": True,
        "namespace": namespace,
        "index": index_name or settings.upstash_search_index,
        "message": f"Scrape completed successfully for {len(pages)} pages",
        "details": {
            "pagesScraped": len(pages),
        },
        "data": pages,
        "homepage": {
            "title": homepage.get("metadata", {}).get("title"),
            "description": homepage.get("metadata", {}).get("description")
            or homepage.get("metadata", {}).get("ogDescription"),
            "favicon": homepage.get("metadata", {}).get("favicon"),
            "ogImage": homepage.get("metadata", {}).get("ogImage")
            or homepage.get("metadata", {}).get("og:image"),
        },
    }
