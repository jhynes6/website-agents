from __future__ import annotations

import asyncio
import html as html_lib
import re
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set, Tuple
from urllib.parse import quote, urldefrag, urljoin, urlparse, urlunparse
from xml.etree import ElementTree as ET

import httpx

from ..config import get_settings
from ..logging import log

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
except Exception:  # pragma: no cover - handled at runtime when provider is selected
    AsyncWebCrawler = None  # type: ignore[assignment]
    BrowserConfig = None  # type: ignore[assignment]
    CrawlerRunConfig = None  # type: ignore[assignment]
    CacheMode = None  # type: ignore[assignment]


class Crawl4AIClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _require_sdk(self) -> None:
        if AsyncWebCrawler is None or BrowserConfig is None or CrawlerRunConfig is None or CacheMode is None:
            raise RuntimeError(
                "crawl4ai is not installed or failed to import. "
                "Install dependency and run crawl4ai browser setup."
            )

    def _browser_config(self) -> "BrowserConfig":
        self._require_sdk()
        return BrowserConfig(
            browser_type="chromium",
            headless=bool(self.settings.crawl4ai_headless),
            verbose=bool(self.settings.crawl4ai_verbose),
            viewport_width=1280,
            viewport_height=720,
        )

    def _run_config(self) -> "CrawlerRunConfig":
        self._require_sdk()
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=int(self.settings.crawl4ai_page_timeout_ms),
            wait_until="domcontentloaded",
            remove_overlay_elements=True,
            scan_full_page=False,
            exclude_external_links=False,
            wait_for_images=False,
            process_iframes=False,
            delay_before_return_html=0.5,
        )

    def _run_config_fallback(self) -> "CrawlerRunConfig":
        """
        Slower but more resilient config for pages that initially return near-empty markdown.
        """
        self._require_sdk()
        timeout_ms = max(int(self.settings.crawl4ai_page_timeout_ms), 90_000)
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=timeout_ms,
            wait_until="networkidle",
            remove_overlay_elements=True,
            scan_full_page=True,
            exclude_external_links=False,
            wait_for_images=True,
            process_iframes=False,
            delay_before_return_html=1.5,
        )

    @staticmethod
    def _root_domain_url(url: str) -> str:
        parsed = urlparse(url)
        scheme = parsed.scheme or "https"
        host = parsed.netloc or parsed.path
        return f"{scheme}://{host}".rstrip("/")

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
        # Encode unsafe URL characters (notably spaces in path/query) for consistent browser navigation.
        path = quote(p.path or "/", safe="/%:@-._~!$&'()*+,;=")
        query = quote(p.query or "", safe="=&%:@-._~!$'()*+,;")
        return urlunparse((p.scheme, p.netloc, path, p.params, query, p.fragment))

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
                resp = await client.get(url)
            if resp.status_code >= 400:
                return None
            return resp.text
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

    @staticmethod
    def _extract_markdown(result: Any) -> str:
        markdown_value = getattr(result, "markdown", None)
        if isinstance(markdown_value, str):
            return markdown_value
        if markdown_value is not None:
            raw_markdown = getattr(markdown_value, "raw_markdown", None)
            if isinstance(raw_markdown, str):
                return raw_markdown
            fit_markdown = getattr(markdown_value, "fit_markdown", None)
            if isinstance(fit_markdown, str):
                return fit_markdown
            if raw_markdown is not None:
                as_text = str(raw_markdown).strip()
                if as_text:
                    return as_text
            as_text = str(markdown_value).strip()
            if as_text:
                return as_text
        extracted = getattr(result, "extracted_content", None)
        if isinstance(extracted, str):
            return extracted
        return ""

    @staticmethod
    def _extract_html(result: Any) -> str:
        for attr in ("cleaned_html", "html", "fit_html"):
            v = getattr(result, attr, None)
            if isinstance(v, str) and v.strip():
                return v
        markdown_value = getattr(result, "markdown", None)
        if markdown_value is not None:
            for attr in ("cleaned_html", "raw_html", "html"):
                v = getattr(markdown_value, attr, None)
                if isinstance(v, str) and v.strip():
                    return v
        return ""

    @staticmethod
    def _html_to_text(raw_html: str) -> str:
        t = raw_html or ""
        if not t:
            return ""
        t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
        t = re.sub(r"(?s)<!--.*?-->", " ", t)
        t = re.sub(r"(?s)<[^>]+>", " ", t)
        t = html_lib.unescape(t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    @staticmethod
    def _is_tiny_content(text: str, *, min_len: int = 30) -> bool:
        return len((text or "").strip()) < min_len

    @staticmethod
    def _extract_title(result: Any, fallback_url: str) -> str:
        metadata = getattr(result, "metadata", None)
        if isinstance(metadata, dict):
            title = str(metadata.get("title") or metadata.get("ogTitle") or "").strip()
            if title:
                return title
        title = str(getattr(result, "title", "") or "").strip()
        return title or fallback_url

    def _extract_links(self, result: Any, current_url: str) -> List[str]:
        links = getattr(result, "links", None)
        if not links:
            return []
        raw_candidates: List[str] = []
        if isinstance(links, dict):
            for value in links.values():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            raw_candidates.append(item)
                        elif isinstance(item, dict):
                            raw_candidates.append(str(item.get("href") or item.get("url") or item.get("link") or ""))
                elif isinstance(value, dict):
                    raw_candidates.append(str(value.get("href") or value.get("url") or value.get("link") or ""))
                elif isinstance(value, str):
                    raw_candidates.append(value)
        elif isinstance(links, list):
            for item in links:
                if isinstance(item, str):
                    raw_candidates.append(item)
                elif isinstance(item, dict):
                    raw_candidates.append(str(item.get("href") or item.get("url") or item.get("link") or ""))

        out: List[str] = []
        seen: Set[str] = set()
        for candidate in raw_candidates:
            normalized = self._normalize_url(candidate, base=current_url)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized)
        return out

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

        # Treat www/non-www as same root host.
        if _canonical(host) == _canonical(seed_host):
            return True

        if host == seed_host:
            return True

        if allow_subdomains:
            if host.endswith("." + seed_host):
                return True
            if seed_host.endswith("." + host):
                return True

        # If crawl_entire_domain is False, keep strict host matching.
        # If True but subdomains are disabled, still stay on exact host.
        return bool(crawl_entire_domain and False)

    async def _scrape_url_async(self, url: str) -> Dict[str, Any]:
        normalized = self._normalize_url(url)
        if not normalized:
            raise ValueError("A valid http(s) URL is required")

        async with AsyncWebCrawler(config=self._browser_config()) as crawler:
            result = await crawler.arun(url=normalized, config=self._run_config())
            success = bool(getattr(result, "success", False))
            if not success:
                error = str(getattr(result, "error_message", "unknown crawl error"))
                raise RuntimeError(f"Crawl4AI scrape failed: {error}")
            markdown = str(self._extract_markdown(result) or "")

            # Retry with fuller rendering if extraction is suspiciously tiny.
            if self._is_tiny_content(markdown):
                log("crawl4ai.scrape.tiny_markdown_retry", {"url": normalized, "first_len": len(markdown)})
                retry_result = await crawler.arun(url=normalized, config=self._run_config_fallback())
                if bool(getattr(retry_result, "success", False)):
                    retry_md = str(self._extract_markdown(retry_result) or "")
                    if not self._is_tiny_content(retry_md):
                        result = retry_result
                        markdown = retry_md
                    else:
                        html_text = self._html_to_text(self._extract_html(retry_result))
                        if not self._is_tiny_content(html_text):
                            result = retry_result
                            markdown = html_text
                else:
                    # Keep first result, but try HTML fallback from it.
                    html_text = self._html_to_text(self._extract_html(result))
                    if not self._is_tiny_content(html_text):
                        markdown = html_text

            # Final fallback: HTML text extraction from whichever result we're returning.
            if self._is_tiny_content(markdown):
                html_text = self._html_to_text(self._extract_html(result))
                if not self._is_tiny_content(html_text):
                    markdown = html_text

            final_url = self._normalize_url(str(getattr(result, "url", "") or ""), base=normalized) or normalized
            title = self._extract_title(result, final_url)
            return {
                "url": final_url,
                "metadata": {"sourceURL": final_url, "title": title},
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
            log(
                "crawl4ai.map.sitemap_ok",
                {
                    "seed_url": normalized,
                    "sitemap_url": sitemap_url,
                    "count": len(sitemap_links),
                },
            )
            return sitemap_links

        pages, status = await self.crawl_and_wait(
            url=normalized,
            limit=effective_limit,
            include_paths=None,
            exclude_paths=None,
            max_depth=min(self.settings.crawl4ai_default_max_depth, 3),
            crawl_entire_domain=True,
            allow_subdomains=allow_subdomains,
        )
        links: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for page in pages:
            page_url = str((page.get("metadata") or {}).get("sourceURL") or page.get("url") or "").strip()
            if not page_url or page_url in seen:
                continue
            seen.add(page_url)
            links.append({"url": page_url})

        for discovered in status.get("discovered_urls", []) or []:
            d = str(discovered or "").strip()
            if not d or d in seen:
                continue
            seen.add(d)
            links.append({"url": d})

        return links[:effective_limit]

    def scrape_url(self, url: str) -> Dict[str, Any]:
        self._require_sdk()
        try:
            return asyncio.run(self._scrape_url_async(url))
        except RuntimeError:
            # Defensive fallback when called from environments with an active event loop.
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
        self._require_sdk()
        seed = self._normalize_url(url)
        if not seed:
            raise ValueError("A valid http(s) URL is required")
        crawl_limit = max(1, int(limit))
        depth_limit = int(max_depth) if isinstance(max_depth, int) and max_depth >= 0 else int(self.settings.crawl4ai_default_max_depth)
        discovered_limit = max(crawl_limit * 8, 100)
        if self.settings.crawl4ai_max_discovered_urls > 0:
            discovered_limit = min(discovered_limit, int(self.settings.crawl4ai_max_discovered_urls))
        if allow_subdomains is None:
            allow_subdomains = bool(self.settings.crawl4ai_allow_subdomains)

        queue: Deque[Tuple[str, int]] = deque([(seed, 0)])
        queued: Set[str] = {seed}
        visited: Set[str] = set()
        discovered_urls: List[str] = []
        pages: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []

        async with AsyncWebCrawler(config=self._browser_config()) as crawler:
            while queue and len(pages) < crawl_limit:
                current_url, depth = queue.popleft()
                if current_url in visited:
                    continue
                visited.add(current_url)

                if not self._is_in_scope(
                    url=current_url,
                    seed_url=seed,
                    crawl_entire_domain=crawl_entire_domain,
                    allow_subdomains=allow_subdomains,
                ):
                    continue

                if not self._passes_filters(
                    url=current_url,
                    include_paths=include_paths,
                    exclude_paths=exclude_paths,
                ):
                    continue

                try:
                    result = await crawler.arun(url=current_url, config=self._run_config())
                    if not bool(getattr(result, "success", False)):
                        error_message = str(getattr(result, "error_message", "unknown crawl error"))
                        errors.append({"url": current_url, "error": error_message})
                        log("crawl4ai.crawl.url_error", {"url": current_url, "error": error_message})
                        continue

                    markdown = str(self._extract_markdown(result) or "")
                    final_url = self._normalize_url(str(getattr(result, "url", "") or ""), base=current_url) or current_url
                    title = self._extract_title(result, final_url)
                    pages.append(
                        {
                            "url": final_url,
                            "metadata": {"sourceURL": final_url, "title": title},
                            "markdown": markdown,
                        }
                    )

                    links = self._extract_links(result, final_url)
                    for link in links:
                        if link in queued or link in visited:
                            continue
                        if not self._is_in_scope(
                            url=link,
                            seed_url=seed,
                            crawl_entire_domain=crawl_entire_domain,
                            allow_subdomains=allow_subdomains,
                        ):
                            continue
                        if len(discovered_urls) < discovered_limit:
                            discovered_urls.append(link)
                        if depth < depth_limit:
                            queue.append((link, depth + 1))
                            queued.add(link)
                except Exception as e:
                    errors.append({"url": current_url, "error": str(e)})
                    log("crawl4ai.crawl.exception", {"url": current_url, "error": str(e)})

        status = {
            "status": "completed" if pages else "failed",
            "total": len(pages),
            "crawled": len(visited),
            "errors": errors,
            "discovered_urls": discovered_urls[:discovered_limit],
        }
        return pages[:crawl_limit], status


crawl4ai_client = Crawl4AIClient()
