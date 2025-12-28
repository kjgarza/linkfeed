"""Markdown URL extraction."""

import re
from pathlib import Path
from typing import Iterator
from linkfeed.utils.url import is_valid_url

# Regex for markdown links: [text](url)
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")

# Regex for bare URLs
BARE_URL_PATTERN = re.compile(
    r"(?<![(\[])https?://[^\s<>\"\'\)]+(?![)\]])", re.IGNORECASE
)


def extract_urls_from_markdown(content: str) -> list[str]:
    """Extract URLs from markdown content."""
    urls = set()

    # Extract markdown link URLs (excluding images)
    for match in MARKDOWN_LINK_PATTERN.finditer(content):
        url = match.group(2).strip()
        if is_valid_url(url):
            urls.add(url)

    # Extract bare URLs
    for match in BARE_URL_PATTERN.finditer(content):
        url = match.group(0).strip()
        # Clean up trailing punctuation
        url = url.rstrip(".,;:!?")
        if is_valid_url(url):
            urls.add(url)

    return list(urls)


def scan_markdown_directory(directory: Path) -> Iterator[str]:
    """Recursively scan a directory for markdown files and extract URLs."""
    if not directory.is_dir():
        return

    for md_file in directory.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            for url in extract_urls_from_markdown(content):
                yield url
        except (IOError, UnicodeDecodeError):
            continue
