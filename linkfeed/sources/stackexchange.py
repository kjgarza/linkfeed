"""StackExchange source via SE API v2.3."""

import logging
from typing import Optional

import aiohttp

from linkfeed.sources.base import BaseSource, register_source

logger = logging.getLogger(__name__)

SE_API_URL = "https://api.stackexchange.com/2.3/questions"


@register_source("stackexchange")
class StackExchangeSource(BaseSource):
    """Fetch question URLs from StackExchange via the API."""

    def __init__(
        self,
        site: str = "stackoverflow",
        tagged: str = "",
        limit: int = 15,
        sort: str = "activity",
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.site = site
        self.tagged = tagged
        self.limit = limit
        self.sort = sort
        self._session = session

    async def fetch_urls(self) -> list[str]:
        """Fetch question URLs from StackExchange."""
        close_session = False
        session = self._session
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            params: dict[str, str | int] = {
                "site": self.site,
                "sort": self.sort,
                "pagesize": self.limit,
                "filter": "default",
            }
            if self.tagged:
                params["tagged"] = self.tagged

            async with session.get(SE_API_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        f"StackExchange API returned status {response.status}"
                    )
                    return []

                data = await response.json()
                items = data.get("items", [])
                urls = []
                for item in items:
                    link = item.get("link")
                    if link:
                        urls.append(link)
                    if len(urls) >= self.limit:
                        break
                return urls
        except Exception as e:
            logger.warning(f"Error fetching from StackExchange: {e}")
            return []
        finally:
            if close_session:
                await session.close()
