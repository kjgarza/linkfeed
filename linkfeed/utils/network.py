"""Network utilities for HTTP fetching."""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
MAX_REDIRECTS = 5
USER_AGENT = "linkfeed/0.1.0 (+https://github.com/linkfeed)"
JINA_BASE_URL = "https://r.jina.ai/"

# Backoff settings for 429 responses
_BACKOFF_BASE = 2.0
_BACKOFF_MAX_RETRIES = 3


@dataclass
class FetchResult:
    """Result of an HTTP fetch operation."""

    content: bytes
    url: str  # Final URL after redirects
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    status_code: int = 200
    fetched_via: str = "direct"


async def _fetch_direct(
    url: str,
    session: aiohttp.ClientSession,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[FetchResult]:
    """Perform a direct aiohttp GET. Returns result even on error status."""
    try:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with session.get(
            url,
            timeout=client_timeout,
            headers={"User-Agent": USER_AGENT},
            max_redirects=MAX_REDIRECTS,
            allow_redirects=True,
        ) as response:
            content = await response.read()

            content_length = None
            if response.headers.get("Content-Length"):
                try:
                    content_length = int(response.headers["Content-Length"])
                except ValueError:
                    pass

            return FetchResult(
                content=content,
                url=str(response.url),
                content_type=response.headers.get("Content-Type"),
                content_length=content_length,
                status_code=response.status,
                fetched_via="direct",
            )
    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching {url}")
        return None
    except aiohttp.TooManyRedirects:
        logger.warning(f"Too many redirects for {url}")
        return None
    except aiohttp.ClientError as e:
        logger.warning(f"Error fetching {url}: {e}")
        return None


async def _fetch_with_backoff(
    url: str,
    session: aiohttp.ClientSession,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[FetchResult]:
    """Wrap _fetch_direct with exponential backoff on 429 responses."""
    for attempt in range(_BACKOFF_MAX_RETRIES + 1):
        result = await _fetch_direct(url, session, timeout)
        if result is None:
            return None
        if result.status_code != 429:
            return result
        if attempt < _BACKOFF_MAX_RETRIES:
            wait = _BACKOFF_BASE ** attempt
            logger.warning(f"Rate limited (429) for {url}, retrying in {wait}s (attempt {attempt + 1}/{_BACKOFF_MAX_RETRIES})")
            await asyncio.sleep(wait)
    return result


def _should_fallback(result: Optional[FetchResult]) -> bool:
    """Return True if the result warrants falling back to Jina."""
    if result is None:
        return True
    if result.status_code in (403, 429):
        return True
    if result.status_code >= 500:
        return True
    if not result.content:
        return True
    return False


async def _fetch_jina(
    url: str,
    session: aiohttp.ClientSession,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[FetchResult]:
    """Fetch via Jina Reader (https://r.jina.ai/{url}), returns markdown content."""
    jina_url = f"{JINA_BASE_URL}{url}"
    headers: dict[str, str] = {"User-Agent": USER_AGENT}

    api_key = os.environ.get("JINA_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with session.get(
            jina_url,
            timeout=client_timeout,
            headers=headers,
            allow_redirects=True,
        ) as response:
            content = await response.read()

            content_length = None
            if response.headers.get("Content-Length"):
                try:
                    content_length = int(response.headers["Content-Length"])
                except ValueError:
                    pass

            return FetchResult(
                content=content,
                url=url,
                content_type=response.headers.get("Content-Type", "text/markdown"),
                content_length=content_length,
                status_code=response.status,
                fetched_via="jina",
            )
    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching via Jina: {url}")
        return None
    except aiohttp.ClientError as e:
        logger.warning(f"Error fetching via Jina {url}: {e}")
        return None


async def fetch_url(
    url: str,
    session: Optional[aiohttp.ClientSession] = None,
    timeout: int = DEFAULT_TIMEOUT,
    enable_fallback: bool = True,
) -> Optional[FetchResult]:
    """Fetch a URL with tiered fallback: direct → Jina Reader."""
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        result = await _fetch_with_backoff(url, session, timeout)

        if enable_fallback and _should_fallback(result):
            logger.info(f"Direct fetch failed/blocked for {url}, trying Jina fallback")
            jina_result = await _fetch_jina(url, session, timeout)
            if jina_result is not None and jina_result.content:
                return jina_result
            logger.warning(f"Jina fallback also failed for {url}")

        return result
    finally:
        if close_session:
            await session.close()


async def head_url(
    url: str,
    session: Optional[aiohttp.ClientSession] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[dict]:
    """Perform a HEAD request to get headers without downloading content."""
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with session.head(
            url,
            timeout=client_timeout,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        ) as response:
            content_length = None
            if response.headers.get("Content-Length"):
                try:
                    content_length = int(response.headers["Content-Length"])
                except ValueError:
                    pass

            return {
                "content_type": response.headers.get("Content-Type"),
                "content_length": content_length,
                "url": str(response.url),
            }
    except aiohttp.ClientError as e:
        logger.warning(f"Error with HEAD request to {url}: {e}")
        return None
    finally:
        if close_session:
            await session.close()


def create_session() -> aiohttp.ClientSession:
    """Create a reusable aiohttp session with connection pooling."""
    connector = aiohttp.TCPConnector(
        limit=100,  # Total connection pool size
        limit_per_host=10,  # Per-host connection limit
    )
    return aiohttp.ClientSession(connector=connector)
