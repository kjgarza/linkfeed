"""Tests for URL source types (HackerNews and StackExchange)."""

from aioresponses import aioresponses
import aiohttp

from linkfeed.sources.base import BaseSource, get_source, get_all_sources, register_source
from linkfeed.sources.hackernews import HackerNewsSource
from linkfeed.sources.stackexchange import StackExchangeSource


class TestSourceRegistry:
    def test_hackernews_registered(self):
        cls = get_source("hackernews")
        assert cls is HackerNewsSource

    def test_stackexchange_registered(self):
        cls = get_source("stackexchange")
        assert cls is StackExchangeSource

    def test_get_unknown_source_returns_none(self):
        assert get_source("nonexistent_source_xyz") is None

    def test_get_all_sources_contains_hn_and_se(self):
        sources = get_all_sources()
        assert "hackernews" in sources
        assert "stackexchange" in sources

    def test_register_source_decorator(self):
        @register_source("test_source_temp")
        class TempSource(BaseSource):
            async def fetch_urls(self) -> list[str]:
                return []

        assert get_source("test_source_temp") is TempSource


class TestHackerNewsSource:
    async def test_returns_urls_from_hits(self):
        mock_response = {
            "hits": [
                {"url": "https://example.com/article1", "title": "Article 1"},
                {"url": "https://example.com/article2", "title": "Article 2"},
                {"url": None, "title": "Ask HN: something"},  # Should be skipped
            ]
        }
        with aioresponses() as m:
            m.get(
                "https://hn.algolia.com/api/v1/search?query=python&tags=story&hitsPerPage=20",
                payload=mock_response,
                status=200,
            )
            source = HackerNewsSource(query="python", limit=20)
            urls = await source.fetch_urls()

        assert "https://example.com/article1" in urls
        assert "https://example.com/article2" in urls
        # Null URL (Ask HN) should be filtered out
        assert None not in urls
        assert len(urls) == 2

    async def test_filters_null_urls(self):
        mock_response = {
            "hits": [
                {"url": None, "title": "Ask HN: help me"},
                {"url": None, "title": "Ask HN: another"},
            ]
        }
        with aioresponses() as m:
            m.get(
                "https://hn.algolia.com/api/v1/search?query=test&tags=story&hitsPerPage=20",
                payload=mock_response,
                status=200,
            )
            source = HackerNewsSource(query="test")
            urls = await source.fetch_urls()

        assert urls == []

    async def test_respects_limit(self):
        mock_response = {
            "hits": [
                {"url": f"https://example.com/article{i}"} for i in range(10)
            ]
        }
        with aioresponses() as m:
            m.get(
                "https://hn.algolia.com/api/v1/search?query=python&tags=story&hitsPerPage=3",
                payload=mock_response,
                status=200,
            )
            source = HackerNewsSource(query="python", limit=3)
            urls = await source.fetch_urls()

        assert len(urls) == 3

    async def test_api_error_returns_empty_list(self):
        with aioresponses() as m:
            m.get(
                "https://hn.algolia.com/api/v1/search?query=python&tags=story&hitsPerPage=20",
                status=500,
                body=b"Internal Server Error",
            )
            source = HackerNewsSource(query="python")
            urls = await source.fetch_urls()

        assert urls == []

    async def test_network_error_returns_empty_list(self):
        with aioresponses() as m:
            m.get(
                "https://hn.algolia.com/api/v1/search?query=python&tags=story&hitsPerPage=20",
                exception=aiohttp.ClientError("connection error"),
            )
            source = HackerNewsSource(query="python")
            urls = await source.fetch_urls()

        assert urls == []

    async def test_uses_provided_session(self):
        mock_response = {
            "hits": [{"url": "https://example.com/article"}]
        }
        with aioresponses() as m:
            m.get(
                "https://hn.algolia.com/api/v1/search?query=test&tags=story&hitsPerPage=20",
                payload=mock_response,
                status=200,
            )
            async with aiohttp.ClientSession() as session:
                source = HackerNewsSource(query="test", session=session)
                urls = await source.fetch_urls()

        assert len(urls) == 1


class TestStackExchangeSource:
    async def test_returns_question_urls(self):
        mock_response = {
            "items": [
                {"link": "https://stackoverflow.com/questions/1/test", "title": "Test Q1"},
                {"link": "https://stackoverflow.com/questions/2/test", "title": "Test Q2"},
            ]
        }
        with aioresponses() as m:
            m.get(
                "https://api.stackexchange.com/2.3/questions?site=stackoverflow&sort=activity&pagesize=15&filter=default&tagged=python",
                payload=mock_response,
                status=200,
            )
            source = StackExchangeSource(site="stackoverflow", tagged="python", limit=15)
            urls = await source.fetch_urls()

        assert "https://stackoverflow.com/questions/1/test" in urls
        assert "https://stackoverflow.com/questions/2/test" in urls

    async def test_api_error_returns_empty_list(self):
        with aioresponses() as m:
            m.get(
                "https://api.stackexchange.com/2.3/questions?site=stackoverflow&sort=activity&pagesize=15&filter=default",
                status=400,
                body=b"Bad Request",
            )
            source = StackExchangeSource()
            urls = await source.fetch_urls()

        assert urls == []

    async def test_network_error_returns_empty_list(self):
        with aioresponses() as m:
            m.get(
                "https://api.stackexchange.com/2.3/questions?site=stackoverflow&sort=activity&pagesize=15&filter=default",
                exception=aiohttp.ClientError("connection error"),
            )
            source = StackExchangeSource()
            urls = await source.fetch_urls()

        assert urls == []

    async def test_defaults(self):
        source = StackExchangeSource()
        assert source.site == "stackoverflow"
        assert source.tagged == ""
        assert source.limit == 15
        assert source.sort == "activity"

    async def test_respects_limit(self):
        mock_response = {
            "items": [
                {"link": f"https://stackoverflow.com/questions/{i}"} for i in range(10)
            ]
        }
        with aioresponses() as m:
            m.get(
                "https://api.stackexchange.com/2.3/questions?site=stackoverflow&sort=activity&pagesize=5&filter=default",
                payload=mock_response,
                status=200,
            )
            source = StackExchangeSource(limit=5)
            urls = await source.fetch_urls()

        assert len(urls) == 5
