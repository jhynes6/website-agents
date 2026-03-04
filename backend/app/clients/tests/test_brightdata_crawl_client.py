import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List


# Ensure backend root is on path when running via pytest from repo root
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.clients.brightdata_crawl_client import BrightDataCrawlClient  # noqa: E402


def test_map_urls_falls_back_to_markdown_links():
    client = BrightDataCrawlClient()

    async def fake_sitemap(
        seed_url: str,
        limit: int,
        sitemap_url: str | None,
        include_paths: List[str] | None = None,
        exclude_paths: List[str] | None = None,
        allow_subdomains: bool | None = None,
    ) -> List[Dict[str, Any]]:
        _ = (seed_url, limit, sitemap_url, include_paths, exclude_paths, allow_subdomains)
        return []

    async def fake_markdown(url: str) -> str:
        _ = url
        return (
            "# Home\n\n"
            "[About](/about)\n"
            "[Blog](https://example.com/blog)\n"
            "[External](https://other.com/page)\n"
        )

    client._map_urls_from_sitemap = fake_sitemap  # type: ignore[method-assign]
    client._request_markdown = fake_markdown  # type: ignore[method-assign]

    links = asyncio.run(client.map_urls("https://example.com", limit=10))
    urls = {str(item.get("url") or "").rstrip("/") for item in links if isinstance(item, dict)}

    assert "https://example.com" in urls
    assert "https://example.com/about" in urls
    assert "https://example.com/blog" in urls
    assert "https://other.com/page" not in urls


def test_crawl_and_wait_uses_mapped_urls():
    client = BrightDataCrawlClient()

    async def fake_map(url: str, limit: int = 500, sitemap_url: str | None = None) -> List[Dict[str, Any]]:
        _ = (url, limit, sitemap_url)
        return [
            {"url": "https://example.com/about"},
            {"url": "https://example.com/contact"},
        ]

    async def fake_markdown(url: str) -> str:
        if "about" in url:
            return "# About\n\nAbout text"
        if "contact" in url:
            return "# Contact\n\nContact text"
        return "# Home\n\nHome text"

    client.map_urls = fake_map  # type: ignore[method-assign]
    client._request_markdown = fake_markdown  # type: ignore[method-assign]

    pages, status = asyncio.run(
        client.crawl_and_wait(
            url="https://example.com",
            limit=2,
            include_paths=None,
            exclude_paths=None,
            max_depth=2,
        )
    )

    assert len(pages) == 2
    assert status.get("status") == "completed"
    assert status.get("provider") == "brightdata"
