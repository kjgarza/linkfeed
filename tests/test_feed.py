"""Tests for feed generation."""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from linkfeed.models import Feed, FeedItem, Author
from linkfeed.feed import (
    merge_feeds,
    write_json_feed,
    read_existing_feed,
)


class TestFeedModels:
    def test_feed_item_to_json(self):
        item = FeedItem(
            id="test-id",
            url="https://example.com/article",
            title="Test Article",
            summary="A test summary",
        )
        data = item.to_json_feed_item()
        assert data["id"] == "test-id"
        assert data["url"] == "https://example.com/article"
        assert data["title"] == "Test Article"

    def test_feed_to_json(self):
        feed = Feed(
            title="Test Feed",
            home_page_url="https://example.com",
            items=[
                FeedItem(id="1", url="https://example.com/1", title="One"),
            ],
        )
        data = feed.to_json_feed()
        assert data["version"] == "https://jsonfeed.org/version/1.1"
        assert data["title"] == "Test Feed"
        assert len(data["items"]) == 1


class TestMergeFeeds:
    def test_merge_new_items(self):
        existing = Feed(title="Test", items=[
            FeedItem(id="old", url="https://example.com/old", title="Old"),
        ])
        new_items = [
            FeedItem(id="new", url="https://example.com/new", title="New"),
        ]
        merged = merge_feeds(existing, new_items, {"title": "Test"})
        assert len(merged.items) == 2
        assert merged.items[0].id == "old"
        assert merged.items[1].id == "new"

    def test_deduplicates(self):
        existing = Feed(title="Test", items=[
            FeedItem(id="dup", url="https://example.com/dup", title="Original"),
        ])
        new_items = [
            FeedItem(id="dup", url="https://example.com/dup", title="Duplicate"),
        ]
        merged = merge_feeds(existing, new_items, {"title": "Test"})
        assert len(merged.items) == 1
        assert merged.items[0].title == "Original"

    def test_empty_existing(self):
        new_items = [
            FeedItem(id="new", url="https://example.com/new", title="New"),
        ]
        merged = merge_feeds(None, new_items, {"title": "Test"})
        assert len(merged.items) == 1


class TestFeedIO:
    def test_write_and_read(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "feed.json"
            feed = Feed(
                title="Test Feed",
                items=[
                    FeedItem(id="1", url="https://example.com/1", title="One"),
                ],
            )
            write_json_feed(feed, path)

            loaded = read_existing_feed(path)
            assert loaded is not None
            assert loaded.title == "Test Feed"
            assert len(loaded.items) == 1
            assert loaded.items[0].id == "1"

    def test_read_nonexistent(self):
        result = read_existing_feed(Path("/nonexistent/feed.json"))
        assert result is None
