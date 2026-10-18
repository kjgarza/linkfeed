"""Base source interface and registry."""

from abc import ABC, abstractmethod
from typing import Optional, Type


class BaseSource(ABC):
    """Abstract base class for URL sources."""

    @abstractmethod
    async def fetch_urls(self) -> list[str]:
        """Fetch and return a list of URLs from this source."""
        pass


# Registry mapping source type names to classes
_sources: dict[str, Type[BaseSource]] = {}


def register_source(name: str):
    """Decorator to register a source class under a given name."""
    def decorator(cls: Type[BaseSource]) -> Type[BaseSource]:
        _sources[name] = cls
        return cls
    return decorator


def get_source(name: str) -> Optional[Type[BaseSource]]:
    """Get a registered source class by name."""
    return _sources.get(name)


def get_all_sources() -> dict[str, Type[BaseSource]]:
    """Get all registered source classes."""
    return dict(_sources)
