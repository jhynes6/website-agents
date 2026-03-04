import sys
from pathlib import Path
from types import SimpleNamespace


# Ensure backend root is on path when running via pytest from repo root
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.clients import crawl_provider  # noqa: E402


def test_get_crawl_client_prefers_brightdata_as_fallback(monkeypatch):
    settings = SimpleNamespace(
        crawler_provider="crawl4ai",
        firecrawl_api_key=None,
        brightdata_api_key="test-brightdata-key",
    )
    primary_client = object()
    fallback_client = object()

    monkeypatch.setattr(crawl_provider, "get_settings", lambda: settings)
    monkeypatch.setitem(
        sys.modules,
        "app.clients.crawl4ai_client",
        SimpleNamespace(crawl4ai_client=primary_client),
    )
    monkeypatch.setitem(
        sys.modules,
        "app.clients.brightdata_crawl_client",
        SimpleNamespace(brightdata_crawl_client=fallback_client),
    )
    crawl_provider.get_crawl_client.cache_clear()

    selected = crawl_provider.get_crawl_client()

    assert isinstance(selected, crawl_provider.FailoverCrawlClient)
    assert selected._primary is primary_client
    assert selected._fallback is fallback_client
    assert selected._fallback_name == "brightdata"

    crawl_provider.get_crawl_client.cache_clear()


def test_get_crawl_client_brightdata_provider_requires_key(monkeypatch):
    settings = SimpleNamespace(
        crawler_provider="brightdata",
        firecrawl_api_key=None,
        brightdata_api_key="",
    )
    monkeypatch.setattr(crawl_provider, "get_settings", lambda: settings)
    crawl_provider.get_crawl_client.cache_clear()

    try:
        crawl_provider.get_crawl_client()
        assert False, "Expected RuntimeError when BRIGHTDATA_API_KEY is missing"
    except RuntimeError as error:
        assert "BRIGHTDATA_API_KEY" in str(error)

    crawl_provider.get_crawl_client.cache_clear()
