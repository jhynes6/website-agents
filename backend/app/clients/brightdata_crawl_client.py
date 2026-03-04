from __future__ import annotations

import asyncio
import re
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set, Tuple
from urllib.parse import quote, urldefrag, urljoin, urlparse, urlunparse
from xml.etree import ElementTree as ET

import httpx

from ..config import get_settings
from ..logging import log


class BrightDataCrawlClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._api_url = "https://api.brightdata.com/request"

    def _api_key(self) -> str:
        key = (self.settings.brightdata_api_key or "").strip()
        if not key:
            raise RuntimeError("BRIGHTDATA_API_KEY is required for Bright Data crawl provider")
        return key

    def _zone(self) -> str:
        return (self.settings.brightdata_zone or "web_unlocker1").strip() or "web_unlocker1"

    async def _request_markdown(self, url: str) -> str:
        payload: Dict[str, Any] = {
            "zone": self._zone(),
            "url": url,
            "format": "raw",
            "data_format": "markdown",
        }
        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(self._api_url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise RuntimeError(f"BrightData error {response.status_code}: {response.text}")
        try:
            data = response.json()
            body = data.get("body") or data.get("content") or ""
            if isinstance(body, str):
                return body
            return str(body)
        except (ValueError, TypeError):
            return response.text or ""

    @staticmethod
    def _normalize_url(url: str, *, base: Optional[str] = None) -> Optional[str]:
        u = (url or "").strip()
        if not u:
            return None
        if base:
            u = urljoin(base, u)
        u = urldefrag(u).url.strip()
        p = urlparse(u)
        if p.scheme not in ("http", "https"):
            return None
        if not p.netloc:
            return None
        path = quote(p.path or "/", safe="/%:@-._~!$&'()*+,;=")
        query = quote(p.query or "", safe="=&%:@-._~!$'()*+,;")
        return urlunparse((p.scheme, p.netloc, path, p.params, query, p.fragment))

    @staticmethod
    def _root_domain_url(url: str) -> str:
        parsed = urlparse(url)
        scheme = parsed.scheme or "https"
        host = parsed.netloc or parsed.path
        return f"{scheme}://{host}".rstrip("/")

    @staticmethod
    def _regex_match(url: str, patterns: Optional[List[str]]) -> bool:
        if not patterns:
            return False
        for pattern in patterns:
            p = str(pattern or "").strip()
            if not p:
                continue
            try:
                if re.search(p, url, re.IGNORECASE):
                    return True
            except re.error:
                if p.lower() in url.lower():
                    return True
        return False

    def _passes_filters(
        self,
        *,
        url: str,
        include_paths: Optional[List[str]],
        exclude_paths: Optional[List[str]],
    ) -> bool:
        if include_paths and not self._regex_match(url, include_paths):
            return False
        if exclude_paths and self._regex_match(url, exclude_paths):
            return False
        return True

    @staticmethod
    def _is_in_scope(
        *,
        url: str,
        seed_url: str,
        crawl_entire_domain: Optional[bool],
        allow_subdomains: Optional[bool],
    ) -> bool:
        parsed = urlparse(url)
        seed = urlparse(seed_url)
        host = (parsed.netloc or "").lower()
        seed_host = (seed.netloc or "").lower()
        if not host or not seed_host:
            return False

        def _canonical(h: str) -> str:
            return h[4:] if h.startswith("www.") else h

        if _canonical(host) == _canonical(seed_host):
            return True
        if host == seed_host:
            return True
        if allow_subdomains:
            if host.endswith("." + seed_host):
                return True
            if seed_host.endswith("." + host):
                return True
        return False

    async def _fetch_text(self, url: str) -> Optional[str]:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
                response = await client.get(url)
            if response.status_code >= 400:
                return None
            return response.text
        except Exception:
            return None

    def _extract_sitemap_locations(self, xml_text: str) -> Tuple[List[str], List[str]]:
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return [], []

        urls: List[str] = []
        nested_sitemaps: List[str] = []
        root_tag = (root.tag or "").lower()
        is_index = root_tag.endswith("sitemapindex")
        is_urlset = root_tag.endswith("urlset")
        if not (is_index or is_urlset):
            return [], []

        for elem in root.iter():
            if not (elem.tag or "").lower().endswith("loc"):
                continue
            loc = (elem.text or "").strip()
            if not loc:
                continue
            normalized = self._normalize_url(loc)
            if not normalized:
                continue
            if is_index:
                nested_sitemaps.append(normalized)
            else:
                urls.append(normalized)
        return urls, nested_sitemaps

    async def _discover_sitemap_urls(self, root_url: str) -> List[str]:
        root = self._root_domain_url(root_url)
        candidates = [
            f"{root}/sitemap.xml",
            f"{root}/sitemap_index.xml",
            f"{root}/sitemap-index.xml",
            f"{root}/sitemaps.xml",
        ]
        robots_url = f"{root}/robots.txt"
        robots_text = await self._fetch_text(robots_url)
        if robots_text:
            for line in robots_text.splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                if k.strip().lower() != "sitemap":
                    continue
                sm = self._normalize_url(v.strip(), base=root)
                if sm:
                    candidates.insert(0, sm)
        deduped: List[str] = []
        seen: Set[str] = set()
        for c in candidates:
            n = self._normalize_url(c, base=root)
            if not n or n in seen:
                continue
            seen.add(n)
            deduped.append(n)
        return deduped

    async def _map_urls_from_sitemap(
        self,
        *,
        seed_url: str,
        limit: int,
        sitemap_url: Optional[str],
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        allow_subdomains: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        root = self._root_domain_url(seed_url)
        start_sitemaps: List[str] = []
        if sitemap_url:
            normalized = self._normalize_url(sitemap_url, base=root)
            if normalized:
                start_sitemaps.append(normalized)
        else:
            start_sitemaps = await self._discover_sitemap_urls(seed_url)

        if not start_sitemaps:
            return []

        queue: Deque[str] = deque(start_sitemaps)
        visited_sitemaps: Set[str] = set()
        seen_urls: Set[str] = set()
        out: List[Dict[str, Any]] = []

        while queue and len(out) < limit:
            sm = queue.popleft()
            if sm in visited_sitemaps:
                continue
            visited_sitemaps.add(sm)
            xml_text = await self._fetch_text(sm)
            if not xml_text:
                continue
            url_entries, nested = self._extract_sitemap_locations(xml_text)
            for nested_sm in nested:
                if nested_sm not in visited_sitemaps:
                    queue.append(nested_sm)

            for u in url_entries:
                if u in seen_urls:
                    continue
                if not self._is_in_scope(
                    url=u,
                    seed_url=seed_url,
                    crawl_entire_domain=True,
                    allow_subdomains=allow_subdomains,
                ):
                    continue
                if not self._passes_filters(url=u, include_paths=include_paths, exclude_paths=exclude_paths):
                    continue
                seen_urls.add(u)
                out.append({"url": u})
                if len(out) >= limit:
                    break
        return out

    def _extract_urls_from_markdown(self, markdown: str, *, base_url: str) -> List[str]:
        candidates: List[str] = []
        candidates.extend(re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown or ""))
        candidates.extend(re.findall(r"<(https?://[^>]+)>", markdown or "", flags=re.IGNORECASE))
        out: List[str] = []
        seen: Set[str] = set()
        for candidate in candidates:
            normalized = self._normalize_url(candidate, base=base_url)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized)
        return out

    @staticmethod
    def _extract_title_from_markdown(markdown: str, fallback_url: str) -> str:
        for line in (markdown or "").splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                if title:
                    return title
        return fallback_url

    async def _scrape_url_async(self, url: str) -> Dict[str, Any]:
        normalized = self._normalize_url(url)
        if not normalized:
            raise ValueError("A valid http(s) URL is required")
        markdown = str(await self._request_markdown(normalized) or "")
        title = self._extract_title_from_markdown(markdown, normalized)
        return {
            "url": normalized,
            "metadata": {"sourceURL": normalized, "title": title},
            "markdown": markdown,
        }

    async def map_urls(
        self,
        url: str,
        limit: int = 500,
        sitemap_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        normalized = self._normalize_url(url)
        if not normalized:
            raise ValueError("A valid http(s) URL is required")

        effective_limit = max(1, int(limit))
        allow_subdomains = bool(self.settings.crawl4ai_allow_subdomains)

        sitemap_links = await self._map_urls_from_sitemap(
            seed_url=normalized,
            limit=effective_limit,
            sitemap_url=sitemap_url,
            allow_subdomains=allow_subdomains,
        )
        if sitemap_links:
            return sitemap_links

        markdown = await self._request_markdown(normalized)
        links = self._extract_urls_from_markdown(markdown, base_url=normalized)
        out: List[Dict[str, Any]] = [{"url": normalized}]
        seen: Set[str] = {normalized}
        for link in links:
            if link in seen:
                continue
            if not self._is_in_scope(
                url=link,
                seed_url=normalized,
                crawl_entire_domain=True,
                allow_subdomains=allow_subdomains,
            ):
                continue
            seen.add(link)
            out.append({"url": link})
            if len(out) >= effective_limit:
                break
        return out[:effective_limit]

    def scrape_url(self, url: str) -> Dict[str, Any]:
        try:
            return asyncio.run(self._scrape_url_async(url))
        except RuntimeError as loop_error:
            if "asyncio.run() cannot be called" not in str(loop_error):
                raise
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._scrape_url_async(url))
            finally:
                loop.close()

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
        seed = self._normalize_url(url)
        if not seed:
            raise ValueError("A valid http(s) URL is required")

        crawl_limit = max(1, int(limit))
        discovered_limit = max(crawl_limit * 8, 100)
        if allow_subdomains is None:
            allow_subdomains = bool(self.settings.crawl4ai_allow_subdomains)

        map_limit = max(crawl_limit * 10, 200)
        mapped_links = await self.map_urls(seed, limit=map_limit)
        candidates: List[str] = [seed]
        candidates.extend(str(item.get("url") or "").strip() for item in mapped_links if isinstance(item, dict))

        deduped_candidates: List[str] = []
        seen: Set[str] = set()
        for candidate in candidates:
            if not candidate:
                continue
            normalized = self._normalize_url(candidate)
            if not normalized or normalized in seen:
                continue
            if not self._is_in_scope(
                url=normalized,
                seed_url=seed,
                crawl_entire_domain=crawl_entire_domain,
                allow_subdomains=allow_subdomains,
            ):
                continue
            if not self._passes_filters(
                url=normalized,
                include_paths=include_paths,
                exclude_paths=exclude_paths,
            ):
                continue
            seen.add(normalized)
            deduped_candidates.append(normalized)
            if len(deduped_candidates) >= discovered_limit:
                break

        sem = asyncio.Semaphore(6)
        pages: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []

        async def _scrape_one(target_url: str) -> None:
            async with sem:
                try:
                    page = await self._scrape_url_async(target_url)
                    pages.append(page)
                except Exception as e:
                    errors.append({"url": target_url, "error": str(e)})
                    log("brightdata.crawl.scrape_error", {"url": target_url, "error": str(e)})

        await asyncio.gather(*[_scrape_one(u) for u in deduped_candidates[:crawl_limit]])

        status = {
            "status": "completed" if pages else "failed",
            "total": len(pages),
            "crawled": len(deduped_candidates[:crawl_limit]),
            "errors": errors,
            "discovered_urls": deduped_candidates[:discovered_limit],
            "provider": "brightdata",
            "max_depth_hint": max_depth,
        }
        return pages[:crawl_limit], status


brightdata_crawl_client = BrightDataCrawlClient()
