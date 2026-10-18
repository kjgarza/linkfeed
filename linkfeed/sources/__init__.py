"""URL source registry and implementations."""

from linkfeed.sources.base import BaseSource, register_source, get_source, get_all_sources
from linkfeed.sources.hackernews import HackerNewsSource
from linkfeed.sources.stackexchange import StackExchangeSource
from linkfeed.sources.qurl import QurlSource

__all__ = [
    "BaseSource",
    "register_source",
    "get_source",
    "get_all_sources",
    "HackerNewsSource",
    "StackExchangeSource",
    "QurlSource",
]
