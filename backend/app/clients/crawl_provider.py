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


_LAUNCH_FAILURE_MARKERS = (
    "crawl4ai browser failed to launch",
    "browsertype.launch",
    "target page, context or browser has been closed",
    "targetclosederror",
    "cannot open shared object file",
    "libnspr4.so",
    "libnss3.so",
)


def _is_launch_failure(error: Exception) -> bool:
    error_name = type(error).__name__.lower()
    if "targetclosederror" in error_name:
        return True
    msg = str(error or "").lower()
    return any(marker in msg for marker in _LAUNCH_FAILURE_MARKERS)


def _trim_error(error: Exception, *, max_chars: int = 700) -> str:
    msg = str(error or "")
    if len(msg) <= max_chars:
        return msg
    return msg[: max_chars - 3] + "..."


class FailoverCrawlClient:
    """
    Use a primary crawler, but auto-fail over when browser launch fails in
    runtime environments missing Playwright shared libraries.
    """

    def __init__(
        self,
        *,
        primary: CrawlClient,
        fallback: CrawlClient,
        primary_name: str = "crawl4ai",
        fallback_name: str = "firecrawl",
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._primary_name = primary_name
        self._fallback_name = fallback_name
        self._failover_active = False

    def _activate_failover(self, *, operation: str, error: Exception) -> None:
        if self._failover_active:
            return
        self._failover_active = True
        log(
            "crawl.provider.failover.activated",
            {
                "operation": operation,
                "from": self._primary_name,
                "to": self._fallback_name,
                "error": _trim_error(error),
            },
        )

    async def map_urls(
        self,
        url: str,
        limit: int = 500,
        sitemap_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self._failover_active:
            return await self._fallback.map_urls(url, limit=limit, sitemap_url=sitemap_url)
        try:
            return await self._primary.map_urls(url, limit=limit, sitemap_url=sitemap_url)
        except Exception as e:
            if not _is_launch_failure(e):
                raise
            self._activate_failover(operation="map_urls", error=e)
            return await self._fallback.map_urls(url, limit=limit, sitemap_url=sitemap_url)

    def scrape_url(self, url: str) -> Dict[str, Any]:
        if self._failover_active:
            return self._fallback.scrape_url(url)
        try:
            return self._primary.scrape_url(url)
        except Exception as e:
            if not _is_launch_failure(e):
                raise
            self._activate_failover(operation="scrape_url", error=e)
            return self._fallback.scrape_url(url)

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
        if self._failover_active:
            return await self._fallback.crawl_and_wait(
                url=url,
                limit=limit,
                include_paths=include_paths,
                exclude_paths=exclude_paths,
                max_depth=max_depth,
                crawl_entire_domain=crawl_entire_domain,
                allow_subdomains=allow_subdomains,
            )
        try:
            return await self._primary.crawl_and_wait(
                url=url,
                limit=limit,
                include_paths=include_paths,
                exclude_paths=exclude_paths,
                max_depth=max_depth,
                crawl_entire_domain=crawl_entire_domain,
                allow_subdomains=allow_subdomains,
            )
        except Exception as e:
            if not _is_launch_failure(e):
                raise
            self._activate_failover(operation="crawl_and_wait", error=e)
            return await self._fallback.crawl_and_wait(
                url=url,
                limit=limit,
                include_paths=include_paths,
                exclude_paths=exclude_paths,
                max_depth=max_depth,
                crawl_entire_domain=crawl_entire_domain,
                allow_subdomains=allow_subdomains,
            )


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

    if provider == "brightdata":
        if not (settings.brightdata_api_key or "").strip():
            raise RuntimeError("CRAWLER_PROVIDER=brightdata requires BRIGHTDATA_API_KEY")
        from .brightdata_crawl_client import brightdata_crawl_client

        log("crawl.provider.selected", {"provider": "brightdata"})
        return brightdata_crawl_client

    from .crawl4ai_client import crawl4ai_client
    brightdata_key = (settings.brightdata_api_key or "").strip()
    if brightdata_key:
        from .brightdata_crawl_client import brightdata_crawl_client

        if provider != "crawl4ai":
            log(
                "crawl.provider.unknown_defaulting",
                {"requested": provider, "using": "crawl4ai", "fallback": "brightdata"},
            )
        else:
            log("crawl.provider.selected", {"provider": "crawl4ai", "fallback": "brightdata"})
        return FailoverCrawlClient(
            primary=crawl4ai_client,
            fallback=brightdata_crawl_client,
            fallback_name="brightdata",
        )

    if provider != "crawl4ai":
        log("crawl.provider.unknown_defaulting", {"requested": provider, "using": "crawl4ai"})
    else:
        log("crawl.provider.selected", {"provider": "crawl4ai"})
    return crawl4ai_client
