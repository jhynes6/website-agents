import asyncio
import time
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
    
    def _post_sync(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Increased timeout to 60s to avoid ReadTimeout on slow scrapes
                with httpx.Client(timeout=60) as client:
                    resp = client.post(url, json=json, headers=self.headers)
                
                if resp.status_code < 400:
                    return resp.json()
                
                # If it's a server error (5xx), wait and retry
                if resp.status_code >= 500:
                    error_msg = f"Firecrawl error {resp.status_code}: {resp.text}"
                    log("firecrawl.retry", {"attempt": attempt + 1, "status": resp.status_code, "error": resp.text})
                    time.sleep(2 * (attempt + 1))
                    last_error = RuntimeError(error_msg)
                    continue
                
                # For 4xx errors, raise immediately
                raise RuntimeError(f"Firecrawl error {resp.status_code}: {resp.text}")
                
            except httpx.RequestError as e:
                log("firecrawl.request_error", {"attempt": attempt + 1, "error": str(e)})
                last_error = e
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 * (attempt + 1))

        # If we get here, we failed after retries
        if last_error:
            raise last_error
        raise RuntimeError(f"Firecrawl failed after {max_retries} attempts")

    async def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Firecrawl error {resp.status_code}: {resp.text}")
        return resp.json()

    async def _get_any(self, url_or_path: str) -> Dict[str, Any]:
        """
        Firecrawl pagination returns an absolute `next` URL. Support both:
        - relative paths like "/crawl/<id>"
        - absolute URLs like "https://api.firecrawl.dev/v2/crawl/<id>?skip=..."
        """
        u = (url_or_path or "").strip()
        if not u:
            raise ValueError("url_or_path required")
        if u.startswith("http://") or u.startswith("https://"):
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(u, headers=self.headers)
            if resp.status_code >= 400:
                raise RuntimeError(f"Firecrawl error {resp.status_code}: {resp.text}")
            return resp.json()
        return await self._get(u)

    async def map_urls(
        self,
        url: str,
        limit: int = 500,
        sitemap_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "url": url,
            "limit": limit,
            "includeSubdomains": True,
            "ignoreQueryParameters": True,
            "sitemap": "include",
        }
        # Firecrawl map does not accept a custom sitemap URL.
        # Keep signature parity with other providers and ignore sitemap_url.
        _ = sitemap_url
        resp = await self._post("/map", payload)
        if isinstance(resp, dict):
            return resp.get("links", [])
        return []

    def scrape_url(self, url: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "url": url,
            # Firecrawl v2 expects options at the top level (no scrapeOptions key)
            "formats": ["markdown"],
            "maxAge": self.settings.crawling_cache_max_age_ms,
            "onlyMainContent": True,
            "removeBase64Images": True,
            "blockAds": True,
            "zeroDataRetention": False,
        }
        return self._post_sync("/scrape", payload)

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
        """Start a crawl and poll until completion."""
        payload: Dict[str, Any] = {
            "url": url,
            "limit": limit,  # Firecrawl v2 crawl limit
            "scrapeOptions": {
                "formats": ["markdown"],
                "maxAge": self.settings.crawling_cache_max_age_ms,
                "onlyMainContent": True,
                "removeBase64Images": True,
                "blockAds": True,
            },
            "zeroDataRetention": False,
        }
        log("firecrawl.crawl.start", {
            "url": url,
            "limit": limit,
            "max_depth": max_depth,
            "include_paths": bool(include_paths),
            "exclude_paths": bool(exclude_paths),
            "payload_limit": payload.get("limit"),
        })
        if include_paths is not None:
            payload["includePaths"] = include_paths
        if exclude_paths is not None:
            payload["excludePaths"] = exclude_paths
        if max_depth is not None:
            # Firecrawl expects maxDiscoveryDepth (not maxDepth)
            payload["maxDiscoveryDepth"] = max_depth
        if crawl_entire_domain is not None:
            payload["crawlEntireDomain"] = bool(crawl_entire_domain)
        if allow_subdomains is not None:
            payload["allowSubdomains"] = bool(allow_subdomains)
        log("firecrawl.crawl.payload", {
            "url": url,
            "limit": payload.get("limit"),
            "maxDiscoveryDepth": payload.get("maxDiscoveryDepth"),
            "includePaths": payload.get("includePaths"),
            "excludePaths": payload.get("excludePaths"),
            "crawlEntireDomain": payload.get("crawlEntireDomain"),
            "allowSubdomains": payload.get("allowSubdomains"),
        })
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
                # Firecrawl can paginate large responses (>10MB) via an absolute `next` URL.
                next_url = status_resp.get("next") if isinstance(status_resp, dict) else None
                total_pages = status_resp.get("total") if isinstance(status_resp, dict) else None
                log("firecrawl.crawl.completed", {
                    "crawl_id": crawl_id,
                    "status": status,
                    "pages_returned": len(data),
                    "limit_requested": limit,
                    "total_pages": total_pages,
                    "has_next": bool(next_url),
                    "next_url": next_url[:100] if next_url else None,
                    "elapsed_ms": int(elapsed * 1000),
                    "response_keys": list(status_resp.keys()) if isinstance(status_resp, dict) else [],
                })
                all_pages: List[Dict[str, Any]] = list(data) if isinstance(data, list) else []
                # Dedupe by source URL
                def _k(p: Dict[str, Any]) -> str:
                    try:
                        m = p.get("metadata") or {}
                        if isinstance(m, dict):
                            return str(m.get("sourceURL") or p.get("url") or "").rstrip("/")
                        return str(p.get("url") or "").rstrip("/")
                    except Exception:
                        return ""
                seen = set()
                deduped: List[Dict[str, Any]] = []
                for p in all_pages:
                    if not isinstance(p, dict):
                        continue
                    key = _k(p)
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    deduped.append(p)
                all_pages = deduped

                # Follow pagination until exhausted OR we reach the requested limit.
                page_fetches = 0
                while next_url and len(all_pages) < limit:
                    page_fetches += 1
                    if page_fetches > 200:
                        log("firecrawl.crawl.next_limit", {"crawl_id": crawl_id, "fetches": page_fetches})
                        break
                    try:
                        next_resp = await self._get_any(str(next_url))
                    except Exception as e:
                        log("firecrawl.crawl.next_error", {"crawl_id": crawl_id, "error": str(e)})
                        break

                    next_data = next_resp.get("data") or []
                    if isinstance(next_data, list):
                        for p in next_data:
                            if not isinstance(p, dict):
                                continue
                            key = _k(p)
                            if not key or key in seen:
                                continue
                            seen.add(key)
                            all_pages.append(p)

                    next_url = next_resp.get("next")
                    log(
                        "firecrawl.crawl.next_page",
                        {
                            "crawl_id": crawl_id,
                            "fetch": page_fetches,
                            "pages_total_collected": len(all_pages),
                            "has_next": bool(next_url),
                            "next_url": str(next_url)[:100] if next_url else None,
                        },
                    )

                return all_pages[:limit], status_resp

        # Timeout reached - return partial data instead of raising error
        log("firecrawl.timeout", {"crawl_id": crawl_id, "elapsed_ms": int(elapsed * 1000)})
        
        # Fetch one last time to ensure we have latest data
        try:
            status_resp = await self._get(f"/crawl/{crawl_id}")
            data = status_resp.get("data") or []
            log("firecrawl.timeout.partial_data", {"count": len(data)})
            return data, status_resp
        except Exception as e:
            log("firecrawl.timeout.error", {"error": str(e)})
            return [], {"status": "timeout_error"}


firecrawl_client = FirecrawlClient()
