from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional, Protocol, Tuple

from ..config import get_settings
from ..logging import log


class CrawlClient(Protocol):
    async def map_urls(
        self,
        url: str,
        limit: int = 500,
        sitemap_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...

    def scrape_url(self, url: str) -> Dict[str, Any]:
        ...

    async def crawl_and_wait(
        self,
        url: str,
        limit: int,
        include_paths: Optional[List[str]],
        exclude_paths: Optional[List[str]],
        max_depth: Optional[int] = None,
        crawl_entire_domain: Optional[bool] = None,
        allow_subdomains: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        ...


@lru_cache(maxsize=1)
def get_crawl_client() -> CrawlClient:
    settings = get_settings()
    provider = (settings.crawler_provider or "crawl4ai").strip().lower()
    if provider == "firecrawl":
        if not (settings.firecrawl_api_key or "").strip():
            raise RuntimeError("CRAWLER_PROVIDER=firecrawl requires FIRECRAWL_API_KEY")
        from .firecrawl import firecrawl_client

        log("crawl.provider.selected", {"provider": "firecrawl"})
        return firecrawl_client

    from .crawl4ai_client import crawl4ai_client

    if provider != "crawl4ai":
        log("crawl.provider.unknown_defaulting", {"requested": provider, "using": "crawl4ai"})
    else:
        log("crawl.provider.selected", {"provider": "crawl4ai"})
    return crawl4ai_client
