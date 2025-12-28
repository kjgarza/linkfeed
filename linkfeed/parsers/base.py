"""Base parser interface and registry."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Type

import aiohttp

from linkfeed.models import FeedItem

if TYPE_CHECKING:
    from openai import AsyncOpenAI


class BaseParser(ABC):
    """Abstract base class for URL parsers."""

    # Priority for parser selection (higher = tried first)
    priority: int = 0

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this parser can handle the given URL."""
        pass

    @abstractmethod
    async def parse(
        self,
        url: str,
        content: bytes,
        content_type: Optional[str],
        content_length: Optional[int] = None,
        session: Optional[aiohttp.ClientSession] = None,
        openai_client: Optional["AsyncOpenAI"] = None,
    ) -> Optional[FeedItem]:
        """Parse the URL content and return a FeedItem."""
        pass


# Registry of parser classes, sorted by priority
_parsers: list[Type[BaseParser]] = []


def register_parser(parser_class: Type[BaseParser]) -> Type[BaseParser]:
    """Register a parser class in the registry."""
    _parsers.append(parser_class)
    _parsers.sort(key=lambda p: p.priority, reverse=True)
    return parser_class


def get_parser(url: str) -> Optional[BaseParser]:
    """Get an appropriate parser for a URL."""
    for parser_class in _parsers:
        if parser_class.can_handle(url):
            return parser_class()
    return None


def get_all_parsers() -> list[Type[BaseParser]]:
    """Get all registered parsers."""
    return list(_parsers)
