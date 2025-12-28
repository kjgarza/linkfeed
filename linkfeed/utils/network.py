"""Network utilities for HTTP fetching."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
MAX_REDIRECTS = 5
USER_AGENT = "linkfeed/0.1.0 (+https://github.com/linkfeed)"


@dataclass
class FetchResult:
    """Result of an HTTP fetch operation."""

    content: bytes
    url: str  # Final URL after redirects
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    status_code: int = 200


async def fetch_url(
    url: str,
    session: Optional[aiohttp.ClientSession] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[FetchResult]:
    """Fetch a URL with timeout and redirect limits."""
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with session.get(
            url,
            timeout=client_timeout,
            headers={"User-Agent": USER_AGENT},
            max_redirects=MAX_REDIRECTS,
            allow_redirects=True,
        ) as response:
            response.raise_for_status()
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
