"""Tests for tiered fallback network fetching."""

import asyncio
from unittest.mock import AsyncMock, patch

import aiohttp
from aioresponses import aioresponses

from linkfeed.utils.network import (
    FetchResult,
    _fetch_direct,
    _fetch_jina,
    _fetch_with_backoff,
    _should_fallback,
    fetch_url,
)


class TestShouldFallback:
    def test_none_result_should_fallback(self):
        assert _should_fallback(None) is True

    def test_403_should_fallback(self):
        result = FetchResult(content=b"Forbidden", url="https://example.com", status_code=403)
        assert _should_fallback(result) is True

    def test_429_should_fallback(self):
        result = FetchResult(content=b"Rate limited", url="https://example.com", status_code=429)
        assert _should_fallback(result) is True

    def test_500_should_fallback(self):
        result = FetchResult(content=b"Server error", url="https://example.com", status_code=500)
        assert _should_fallback(result) is True

    def test_503_should_fallback(self):
        result = FetchResult(content=b"Service unavailable", url="https://example.com", status_code=503)
        assert _should_fallback(result) is True

    def test_empty_content_should_fallback(self):
        result = FetchResult(content=b"", url="https://example.com", status_code=200)
        assert _should_fallback(result) is True

    def test_200_with_content_no_fallback(self):
        result = FetchResult(content=b"<html>content</html>", url="https://example.com", status_code=200)
        assert _should_fallback(result) is False

    def test_301_no_fallback(self):
        result = FetchResult(content=b"Moved", url="https://example.com", status_code=301)
        assert _should_fallback(result) is False


class TestFetchDirect:
    async def test_direct_success(self):
        with aioresponses() as m:
            m.get("https://example.com", status=200, body=b"<html>hello</html>",
                  headers={"Content-Type": "text/html"})
            async with aiohttp.ClientSession() as session:
                result = await _fetch_direct("https://example.com", session)

        assert result is not None
        assert result.status_code == 200
        assert result.content == b"<html>hello</html>"
        assert result.fetched_via == "direct"

    async def test_direct_returns_403_without_raising(self):
        with aioresponses() as m:
            m.get("https://example.com", status=403, body=b"Forbidden")
            async with aiohttp.ClientSession() as session:
                result = await _fetch_direct("https://example.com", session)

        assert result is not None
        assert result.status_code == 403
        assert result.fetched_via == "direct"

    async def test_timeout_returns_none(self):
        with aioresponses() as m:
            m.get("https://example.com", exception=asyncio.TimeoutError())
            async with aiohttp.ClientSession() as session:
                result = await _fetch_direct("https://example.com", session)

        assert result is None

    async def test_client_error_returns_none(self):
        with aioresponses() as m:
            m.get("https://example.com", exception=aiohttp.ClientError("connection refused"))
            async with aiohttp.ClientSession() as session:
                result = await _fetch_direct("https://example.com", session)

        assert result is None


class TestFetchWithBackoff:
    async def test_success_no_retry(self):
        with aioresponses() as m:
            m.get("https://example.com", status=200, body=b"content")
            async with aiohttp.ClientSession() as session:
                result = await _fetch_with_backoff("https://example.com", session)

        assert result is not None
        assert result.status_code == 200

    async def test_429_triggers_retry_then_success(self):
        with aioresponses() as m:
            m.get("https://example.com", status=429, body=b"rate limited")
            m.get("https://example.com", status=200, body=b"content")
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                async with aiohttp.ClientSession() as session:
                    result = await _fetch_with_backoff("https://example.com", session)

        assert result is not None
        assert result.status_code == 200
        mock_sleep.assert_called_once()

    async def test_429_max_retries_exhausted(self):
        with aioresponses() as m:
            # 4 attempts total (1 + 3 retries)
            for _ in range(4):
                m.get("https://example.com", status=429, body=b"rate limited")
            with patch("asyncio.sleep", new_callable=AsyncMock):
                async with aiohttp.ClientSession() as session:
                    result = await _fetch_with_backoff("https://example.com", session)

        assert result is not None
        assert result.status_code == 429


class TestFetchJina:
    async def test_jina_fetches_markdown(self):
        with aioresponses() as m:
            m.get(
                "https://r.jina.ai/https://example.com",
                status=200,
                body=b"# Title\nSome markdown content",
                headers={"Content-Type": "text/markdown"},
            )
            async with aiohttp.ClientSession() as session:
                result = await _fetch_jina("https://example.com", session)

        assert result is not None
        assert result.fetched_via == "jina"
        assert result.content == b"# Title\nSome markdown content"
        assert result.url == "https://example.com"

    async def test_jina_uses_api_key_when_set(self, monkeypatch):
        monkeypatch.setenv("JINA_API_KEY", "test-key-123")

        with aioresponses() as m:
            m.get(
                "https://r.jina.ai/https://example.com",
                status=200,
                body=b"content",
            )
            async with aiohttp.ClientSession() as session:
                result = await _fetch_jina("https://example.com", session)

        assert result is not None

    async def test_jina_timeout_returns_none(self):
        with aioresponses() as m:
            m.get(
                "https://r.jina.ai/https://example.com",
                exception=asyncio.TimeoutError(),
            )
            async with aiohttp.ClientSession() as session:
                result = await _fetch_jina("https://example.com", session)

        assert result is None


class TestFetchUrl:
    async def test_direct_success_no_fallback_needed(self):
        with aioresponses() as m:
            m.get("https://example.com", status=200, body=b"<html>page</html>")
            result = await fetch_url("https://example.com")

        assert result is not None
        assert result.fetched_via == "direct"
        assert result.status_code == 200

    async def test_403_triggers_jina_fallback(self):
        with aioresponses() as m:
            m.get("https://example.com", status=403, body=b"Forbidden")
            m.get(
                "https://r.jina.ai/https://example.com",
                status=200,
                body=b"# Fallback content",
            )
            result = await fetch_url("https://example.com")

        assert result is not None
        assert result.fetched_via == "jina"

    async def test_direct_none_triggers_jina_fallback(self):
        with aioresponses() as m:
            m.get("https://example.com", exception=aiohttp.ClientError("error"))
            m.get(
                "https://r.jina.ai/https://example.com",
                status=200,
                body=b"# Fallback content",
            )
            result = await fetch_url("https://example.com")

        assert result is not None
        assert result.fetched_via == "jina"

    async def test_both_fail_returns_direct_result(self):
        """When Jina fallback also fails, returns the original direct result."""
        with aioresponses() as m:
            m.get("https://example.com", status=403, body=b"Forbidden")
            m.get(
                "https://r.jina.ai/https://example.com",
                exception=aiohttp.ClientError("jina error"),
            )
            result = await fetch_url("https://example.com")

        # Returns the direct 403 result when Jina also fails
        assert result is not None
        assert result.status_code == 403
        assert result.fetched_via == "direct"

    async def test_fallback_disabled(self):
        with aioresponses() as m:
            m.get("https://example.com", status=403, body=b"Forbidden")
            result = await fetch_url("https://example.com", enable_fallback=False)

        assert result is not None
        assert result.status_code == 403
        assert result.fetched_via == "direct"

    async def test_fetched_via_field_direct(self):
        with aioresponses() as m:
            m.get("https://example.com", status=200, body=b"content")
            result = await fetch_url("https://example.com")

        assert result is not None
        assert result.fetched_via == "direct"
