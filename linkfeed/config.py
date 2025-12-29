"""Configuration loading and validation."""

from pathlib import Path
from typing import Optional, Union
import yaml
from pydantic import BaseModel, Field


class FeedConfig(BaseModel):
    """Feed metadata configuration."""

    title: str = "Untitled Feed"
    home_page_url: Optional[str] = None
    feed_url: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None


class TrelloSource(BaseModel):
    """Trello board source configuration."""

    file: str  # Path to Trello JSON export
    lists: list[str] = Field(default_factory=list)  # Filter by list IDs


class SingleFeedConfig(BaseModel):
    """Configuration for a single feed (legacy format)."""

    feed: FeedConfig = Field(default_factory=FeedConfig)
    sources: list[str] = Field(default_factory=list)
    blacklist: list[str] = Field(default_factory=list)
    whitelist: list[str] = Field(default_factory=list)
    website: Optional[str] = None  # URL to scrape for links
    markdown_dir: Optional[str] = None  # Directory to scan for markdown files
    trello: Optional[TrelloSource] = None  # Trello board source


class NamedFeedConfig(BaseModel):
    """Configuration for a named feed in multi-feed setup."""

    name: str  # Used for output folder name
    feed: FeedConfig = Field(default_factory=FeedConfig)
    sources: list[str] = Field(default_factory=list)
    blacklist: list[str] = Field(default_factory=list)
    whitelist: list[str] = Field(default_factory=list)
    website: Optional[str] = None
    markdown_dir: Optional[str] = None
    trello: Optional[TrelloSource] = None
    output_dir: Optional[str] = None  # Custom output directory


class MultiConfig(BaseModel):
    """Multi-feed configuration."""

    feeds: list[NamedFeedConfig] = Field(default_factory=list)
    global_blacklist: list[str] = Field(default_factory=list)  # Applied to all feeds
    global_whitelist: list[str] = Field(default_factory=list)  # Applied to all feeds


# Alias for backward compatibility
Config = SingleFeedConfig


def load_config(path: Path) -> SingleFeedConfig:
    """Load single-feed configuration from a YAML file (legacy format)."""
    if not path.exists():
        return SingleFeedConfig()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

    # Parse feed config
    feed_data = data.get("feed", {})
    feed_config = FeedConfig(**feed_data)

    # Parse trello config
    trello = None
    trello_data = data.get("trello")
    if trello_data:
        trello = TrelloSource(
            file=trello_data.get("file", ""),
            lists=trello_data.get("lists", []),
        )

    return SingleFeedConfig(
        feed=feed_config,
        sources=data.get("sources", []),
        blacklist=data.get("blacklist", []),
        whitelist=data.get("whitelist", []),
        website=data.get("website"),
        markdown_dir=data.get("markdown_dir"),
        trello=trello,
    )


def load_multi_config(path: Path) -> MultiConfig:
    """Load multi-feed configuration from a YAML file."""
    if not path.exists():
        raise ValueError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

    # Check if this is a multi-feed config
    if "feeds" not in data:
        raise ValueError("Multi-feed config must have 'feeds' key")

    feeds = []
    for feed_data in data.get("feeds", []):
        feed_meta = feed_data.get("feed", {})

        # Parse trello config
        trello = None
        trello_data = feed_data.get("trello")
        if trello_data:
            trello = TrelloSource(
                file=trello_data.get("file", ""),
                lists=trello_data.get("lists", []),
            )

        feeds.append(NamedFeedConfig(
            name=feed_data.get("name", "unnamed"),
            feed=FeedConfig(**feed_meta),
            sources=feed_data.get("sources", []),
            blacklist=feed_data.get("blacklist", []),
            whitelist=feed_data.get("whitelist", []),
            website=feed_data.get("website"),
            markdown_dir=feed_data.get("markdown_dir"),
            trello=trello,
            output_dir=feed_data.get("output_dir"),
        ))

    return MultiConfig(
        feeds=feeds,
        global_blacklist=data.get("global_blacklist", []),
        global_whitelist=data.get("global_whitelist", []),
    )


def load_config_dir(config_dir: Path) -> MultiConfig:
    """Load multiple feed configs from a directory of YAML files."""
    if not config_dir.is_dir():
        raise ValueError(f"Config directory not found: {config_dir}")

    feeds = []
    for yaml_file in sorted(config_dir.glob("*.yaml")):
        try:
            single = load_config(yaml_file)
            # Use filename (without extension) as feed name
            name = yaml_file.stem
            feeds.append(NamedFeedConfig(
                name=name,
                feed=single.feed,
                sources=single.sources,
                blacklist=single.blacklist,
                whitelist=single.whitelist,
                website=single.website,
            ))
        except ValueError:
            continue

    return MultiConfig(feeds=feeds)


def is_multi_config(path: Path) -> bool:
    """Check if a config file is multi-feed format."""
    if not path.exists():
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return "feeds" in data
    except yaml.YAMLError:
        return False
