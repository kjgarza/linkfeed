"""Feed generation for JSON Feed and RSS."""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from feedgen.feed import FeedGenerator

from linkfeed.models import Feed, FeedItem

logger = logging.getLogger(__name__)

# Regex to match XML-incompatible control characters (except tab, newline, carriage return)
XML_INVALID_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_for_xml(text: Optional[str]) -> Optional[str]:
    """Remove control characters that are invalid in XML."""
    if text is None:
        return None
    return XML_INVALID_CHARS.sub("", text)


def read_existing_feed(path: Path) -> Optional[Feed]:
    """Read an existing JSON Feed file."""
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Feed.from_json_feed(data)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error reading existing feed: {e}")
        return None


def write_json_feed(feed: Feed, path: Path) -> None:
    """Write a JSON Feed to file."""
    data = feed.to_json_feed()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def merge_feeds(existing: Optional[Feed], new_items: list[FeedItem], feed_meta: dict) -> Feed:
    """Merge new items into an existing feed, deduplicating by ID."""
    if existing:
        existing_ids = {item.id for item in existing.items}
        # Filter out duplicates
        unique_new = [item for item in new_items if item.id not in existing_ids]
        # Append new items (ingestion order)
        all_items = existing.items + unique_new
    else:
        all_items = new_items

    return Feed(
        title=feed_meta.get("title", "Untitled Feed"),
        home_page_url=feed_meta.get("home_page_url"),
        feed_url=feed_meta.get("feed_url"),
        description=feed_meta.get("description"),
        language=feed_meta.get("language"),
        items=all_items,
    )


def generate_rss(feed: Feed, path: Path) -> None:
    """Generate RSS 2.0 from a JSON Feed."""
    fg = FeedGenerator()

    fg.title(feed.title)
    # RSS requires a link, use home_page_url or a placeholder
    link = feed.home_page_url or "https://example.com"
    fg.link(href=link, rel="alternate")
    if feed.feed_url:
        fg.link(href=feed.feed_url, rel="self")
    if feed.description:
        fg.description(feed.description)
    else:
        fg.description(feed.title)  # RSS requires description
    if feed.language:
        fg.language(feed.language)

    def _get_sort_date(item: FeedItem) -> datetime:
        """Get a timezone-aware datetime for sorting."""
        if item.date_published is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        # Make naive datetimes timezone-aware (assume UTC)
        if item.date_published.tzinfo is None:
            return item.date_published.replace(tzinfo=timezone.utc)
        return item.date_published

    # Sort items by date (newest first) for RSS
    sorted_items = sorted(
        feed.items,
        key=_get_sort_date,
        reverse=True,
    )

    for item in sorted_items:
        fe = fg.add_entry()
        fe.id(item.id)
        fe.link(href=item.url)

        title = sanitize_for_xml(item.title) or item.url
        fe.title(title)

        if item.summary:
            fe.description(sanitize_for_xml(item.summary))
        elif item.content_html:
            fe.description(sanitize_for_xml(item.content_html))

        if item.date_published:
            # Ensure timezone-aware datetime for feedgen
            pub_date = item.date_published
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            fe.published(pub_date)

        if item.authors:
            for author in item.authors:
                if author.name:
                    fe.author({"name": sanitize_for_xml(author.name)})

        # Add enclosures for attachments
        for attachment in item.attachments:
            fe.enclosure(
                url=attachment.url,
                type=attachment.mime_type,
                length=str(attachment.size_in_bytes or 0),
            )

        # Add tags as categories
        for tag in item.tags:
            fe.category(term=sanitize_for_xml(tag))

    fg.rss_file(str(path), pretty=True)
