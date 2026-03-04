import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend root is on path when running via pytest from repo root
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.clients.crawl_provider import FailoverCrawlClient, _is_launch_failure  # noqa: E402


class StubClient:
    def __init__(self) -> None:
        self.map_calls = 0
        self.scrape_calls = 0
        self.crawl_calls = 0
        self.map_error: Optional[Exception] = None
        self.scrape_error: Optional[Exception] = None
        self.crawl_error: Optional[Exception] = None

    async def map_urls(
        self,
        url: str,
        limit: int = 500,
        sitemap_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self.map_calls += 1
        _ = (url, limit, sitemap_url)
        if self.map_error:
            raise self.map_error
        return [{"url": "https://fallback.example/ok"}]

    def scrape_url(self, url: str) -> Dict[str, Any]:
        self.scrape_calls += 1
        _ = url
        if self.scrape_error:
            raise self.scrape_error
        return {"url": "https://fallback.example/ok", "markdown": "ok", "metadata": {"sourceURL": "https://fallback.example/ok"}}

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
        self.crawl_calls += 1
        _ = (url, limit, include_paths, exclude_paths, max_depth, crawl_entire_domain, allow_subdomains)
        if self.crawl_error:
            raise self.crawl_error
        return [{"url": "https://fallback.example/ok", "metadata": {"sourceURL": "https://fallback.example/ok"}, "markdown": "ok"}], {"status": "done"}


def test_launch_failure_detector_markers():
    assert _is_launch_failure(RuntimeError("Crawl4AI browser failed to launch"))
    assert _is_launch_failure(RuntimeError("error while loading shared libraries: libnspr4.so"))
    assert _is_launch_failure(RuntimeError("BrowserType.launch: Target page, context or browser has been closed"))
    assert not _is_launch_failure(RuntimeError("HTTP 429 Too Many Requests"))


def test_map_urls_failover_is_sticky():
    primary = StubClient()
    fallback = StubClient()
    primary.map_error = RuntimeError("error while loading shared libraries: libnspr4.so")
    client = FailoverCrawlClient(primary=primary, fallback=fallback)

    first = asyncio.run(client.map_urls("https://example.com", limit=10))
    second = asyncio.run(client.map_urls("https://example.com", limit=10))

    assert first and second
    assert primary.map_calls == 1
    assert fallback.map_calls == 2
    assert client._failover_active is True


def test_non_launch_error_does_not_failover():
    primary = StubClient()
    fallback = StubClient()
    primary.map_error = RuntimeError("upstream timeout")
    client = FailoverCrawlClient(primary=primary, fallback=fallback)

    try:
        asyncio.run(client.map_urls("https://example.com", limit=10))
        assert False, "Expected map_urls to raise for non-launch errors"
    except RuntimeError as e:
        assert "upstream timeout" in str(e)

    assert client._failover_active is False
    assert fallback.map_calls == 0


def test_scrape_url_failover_and_reuse():
    primary = StubClient()
    fallback = StubClient()
    primary.scrape_error = RuntimeError("BrowserType.launch: Target page, context or browser has been closed")
    client = FailoverCrawlClient(primary=primary, fallback=fallback)

    first = client.scrape_url("https://example.com")
    second = client.scrape_url("https://example.com")

    assert first.get("markdown") == "ok"
    assert second.get("markdown") == "ok"
    assert primary.scrape_calls == 1
    assert fallback.scrape_calls == 2
    assert client._failover_active is True


def test_crawl_and_wait_failover():
    class TargetClosedError(Exception):
        pass

    primary = StubClient()
    fallback = StubClient()
    primary.crawl_error = TargetClosedError("browser closed")
    client = FailoverCrawlClient(primary=primary, fallback=fallback)

    pages, status = asyncio.run(
        client.crawl_and_wait(
            url="https://example.com",
            limit=5,
            include_paths=None,
            exclude_paths=None,
            max_depth=2,
        )
    )

    assert len(pages) == 1
    assert status.get("status") == "done"
    assert primary.crawl_calls == 1
    assert fallback.crawl_calls == 1
    assert client._failover_active is True
