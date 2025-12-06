import asyncio
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..config import get_settings
from ..logging import log


class FirecrawlClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = str(self.settings.firecrawl_base_url).rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=json, headers=self.headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Firecrawl error {resp.status_code}: {resp.text}")
        return resp.json()

    async def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Firecrawl error {resp.status_code}: {resp.text}")
        return resp.json()

    async def map_urls(self, url: str, limit: int = 500) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "url": url,
            "limit": limit,
            "includeSubdomains": True,
            "ignoreQueryParameters": True,
            "sitemap": "include",
        }
        resp = await self._post("/map", payload)
        if isinstance(resp, dict):
            return resp.get("links", [])
        return []

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "url": url,
            # Firecrawl v2 expects options at the top level (no scrapeOptions key)
            "formats": ["markdown", "html"],
            "maxAge": self.settings.crawling_cache_max_age_ms,
            "onlyMainContent": True,
            "removeBase64Images": True,
            "blockAds": True,
            "zeroDataRetention": False,
        }
        return await self._post("/scrape", payload)

    async def crawl_and_wait(
        self,
        url: str,
        limit: int,
        include_paths: Optional[List[str]],
        exclude_paths: Optional[List[str]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Start a crawl and poll until completion."""
        payload: Dict[str, Any] = {
            "url": url,
            "limit": limit,
            "scrapeOptions": {
                "formats": ["markdown", "html"],
                "maxAge": self.settings.crawling_cache_max_age_ms,
                "onlyMainContent": True,
                "removeBase64Images": True,
                "blockAds": True,
            },
            "zeroDataRetention": False,
        }
        if include_paths is not None:
            payload["includePaths"] = include_paths
        if exclude_paths is not None:
            payload["excludePaths"] = exclude_paths
        start_resp = await self._post("/crawl", payload)
        crawl_id = start_resp.get("id")
        if not crawl_id:
            raise RuntimeError(f"Firecrawl did not return a crawl id: {start_resp}")

        poll_interval = self.settings.firecrawl_poll_interval_ms / 1000
        timeout = self.settings.firecrawl_poll_timeout_ms / 1000
        elapsed = 0.0

        while elapsed < timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            status_resp = await self._get(f"/crawl/{crawl_id}")
            status = status_resp.get("status")
            log("firecrawl.poll", {"status": status, "elapsed_ms": int(elapsed * 1000)})

            if status in ("completed", "failed"):
                data = status_resp.get("data") or []
                return data, status_resp

        raise TimeoutError("Firecrawl crawl did not complete before timeout")


firecrawl_client = FirecrawlClient()

