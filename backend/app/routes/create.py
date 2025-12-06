import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from ..clients.firecrawl import firecrawl_client
from ..clients.upstash_search import upstash_search_client
from ..config import get_settings
from ..logging import log

router = APIRouter()


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

    documents = []
    for index, page in enumerate(pages):
        full_content = page.get("markdown") or page.get("content") or ""
        title = page.get("metadata", {}).get("title") or "Untitled"
        page_url = page.get("metadata", {}).get("sourceURL") or page.get("url") or ""
        description = page.get("metadata", {}).get("description") or page.get("metadata", {}).get("ogDescription") or ""

        searchable_text = f"namespace:{namespace} {title} {description} {full_content}"[:1000]

        documents.append(
            {
                "id": f"{namespace}-{index}",
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
        result = await firecrawl_client.scrape_url(target)
        data = result.get("data") if isinstance(result, dict) else None
        if data:
            data["url"] = target
            pages.append(data)

    if not pages:
        raise HTTPException(status_code=502, detail="Scrape returned no pages")

    documents = []
    for index, page in enumerate(pages):
        full_content = page.get("markdown") or page.get("content") or ""
        metadata = page.get("metadata", {}) or {}
        title = metadata.get("title") or "Untitled"
        page_url = metadata.get("sourceURL") or metadata.get("url") or page.get("url") or ""
        description = metadata.get("description") or metadata.get("ogDescription") or ""

        searchable_text = f"namespace:{namespace} {title} {description} {full_content}"[:1000]

        documents.append(
            {
                "id": f"{namespace}-{index}",
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
                },
            }
        )

    log("scrape.upsert", {"index": index_name or settings.upstash_search_index, "docs": len(documents)})
    await upstash_search_client.upsert_documents(documents, index_name=index_name)

    homepage = pages[0]
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

