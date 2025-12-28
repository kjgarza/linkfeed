"""Trello board JSON URL extraction."""

import json
import logging
import re
from pathlib import Path
from typing import Iterator, Optional

from linkfeed.utils.url import is_valid_url

logger = logging.getLogger(__name__)

# Regex for bare URLs in text
BARE_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"\'\)\]]+", re.IGNORECASE
)

# Trello URLs to filter out
TRELLO_DOMAINS = {"trello.com", "www.trello.com"}


def extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs from free-form text."""
    if not text:
        return []

    urls = set()
    for match in BARE_URL_PATTERN.finditer(text):
        url = match.group(0).strip()
        # Clean up trailing punctuation
        url = url.rstrip(".,;:!?|")

        if is_valid_url(url):
            # Filter out Trello's own URLs
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            if domain not in TRELLO_DOMAINS:
                urls.add(url)

    return list(urls)


def parse_trello_card(card: dict) -> list[str]:
    """Extract URLs from a Trello card's name and description."""
    urls = []

    # Extract from card name (title)
    name = card.get("name") or ""
    urls.extend(extract_urls_from_text(name))

    # Extract from card description
    desc = card.get("desc") or ""
    urls.extend(extract_urls_from_text(desc))

    return urls


def parse_trello_board(
    path: Path,
    list_ids: Optional[list[str]] = None,
) -> Iterator[str]:
    """Parse a Trello board JSON export and extract URLs from cards.

    Args:
        path: Path to the Trello board JSON file
        list_ids: Optional list of idList values to filter cards by

    Yields:
        URLs found in card titles and descriptions
    """
    if not path.exists():
        logger.warning(f"Trello board file not found: {path}")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            board = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error reading Trello board: {e}")
        return

    cards = board.get("cards", [])
    if not cards:
        logger.warning(f"No cards found in Trello board: {path}")
        return

    # Convert list_ids to set for faster lookup
    filter_lists = set(list_ids) if list_ids else None

    seen_urls = set()

    for card in cards:
        # Skip closed cards
        if card.get("closed", False):
            continue

        # Filter by list ID if specified
        if filter_lists and card.get("idList") not in filter_lists:
            continue

        # Extract URLs from card
        for url in parse_trello_card(card):
            if url not in seen_urls:
                seen_urls.add(url)
                yield url


def get_list_names(path: Path) -> dict[str, str]:
    """Get a mapping of list IDs to list names for reference.

    Args:
        path: Path to the Trello board JSON file

    Returns:
        Dict mapping list ID to list name
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            board = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

    lists = board.get("lists", [])
    return {lst["id"]: lst["name"] for lst in lists if "id" in lst and "name" in lst}
