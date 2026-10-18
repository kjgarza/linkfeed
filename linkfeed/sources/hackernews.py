"""HackerNews source via Algolia API."""

import logging
from typing import Optional

import aiohttp

from linkfeed.sources.base import BaseSource, register_source

logger = logging.getLogger(__name__)

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


@register_source("hackernews")
class HackerNewsSource(BaseSource):
    """Fetch story URLs from HackerNews via the Algolia search API."""

    def __init__(
        self,
        query: str,
        limit: int = 20,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.query = query
        self.limit = limit
        self._session = session

    async def fetch_urls(self) -> list[str]:
        """Fetch URLs from HackerNews matching the query."""
        close_session = False
        session = self._session
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            params = {
                "query": self.query,
                "tags": "story",
                "hitsPerPage": self.limit,
            }
            async with session.get(HN_ALGOLIA_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        f"HackerNews API returned status {response.status}"
                    )
                    return []

                data = await response.json()
                hits = data.get("hits", [])
                urls = []
                for hit in hits:
                    url = hit.get("url")
                    if url:  # Skip Ask HN and similar posts with null URLs
                        urls.append(url)
                    if len(urls) >= self.limit:
                        break
                return urls
        except Exception as e:
            logger.warning(f"Error fetching from HackerNews: {e}")
            return []
        finally:
            if close_session:
                await session.close()
