"""Tests for rebuild functionality."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from linkfeed.cli import main
from linkfeed.models import Feed, FeedItem


@pytest.fixture
def temp_feed_dir(tmp_path):
    """Create a temporary directory with an existing feed."""
    feed_dir = tmp_path / "feeds"
    feed_dir.mkdir()
    
    # Create existing feed with 2 items
    existing_feed = Feed(
        version="https://jsonfeed.org/version/1.1",
        title="Test Feed",
        home_page_url="https://example.com",
        items=[
            FeedItem(
                id="existing-1",
                url="https://example.com/old1",
                title="Old Item 1",
            ),
            FeedItem(
                id="existing-2",
                url="https://example.com/old2",
                title="Old Item 2",
            ),
        ],
    )
    
    json_file = feed_dir / "feed.json"
    with open(json_file, "w") as f:
        json.dump(existing_feed.to_json_feed(), f)
    
    return feed_dir


class TestRebuildFlag:
    """Test the --rebuild flag functionality."""

    def test_rebuild_discards_existing_feed(self, temp_feed_dir, monkeypatch):
        """Test that --rebuild flag discards existing feed."""
        runner = CliRunner()
        
        config_path = temp_feed_dir / "config.yaml"
        config_path.write_text("""
feed:
  title: "Test Feed"
sources:
  - https://example.com/new1
  - https://example.com/new2
""")
        
        json_out = temp_feed_dir / "feed.json"
        
        # Mock the processing to avoid actual network calls
        with patch("linkfeed.cli.process_urls") as mock_process:
            mock_process.return_value = [
                FeedItem(
                    id="new-1",
                    url="https://example.com/new1",
                    title="New Item 1",
                ),
                FeedItem(
                    id="new-2",
                    url="https://example.com/new2",
                    title="New Item 2",
                ),
            ]
            
            result = runner.invoke(main, [
                "--config", str(config_path),
                "--json-out", str(json_out),
                "--rebuild",
            ])
        
        # Check that feed was rebuilt
        assert result.exit_code == 0
        assert "Rebuilt feed with 2 items" in result.output
        
        # Verify the feed only contains new items
        with open(json_out) as f:
            feed_data = json.load(f)
        
        assert len(feed_data["items"]) == 2
        item_urls = [item["url"] for item in feed_data["items"]]
        assert "https://example.com/new1" in item_urls
        assert "https://example.com/new2" in item_urls
        assert "https://example.com/old1" not in item_urls

    def test_without_rebuild_appends_to_existing(self, temp_feed_dir):
        """Test that without --rebuild, new items are appended."""
        runner = CliRunner()
        
        config_path = temp_feed_dir / "config.yaml"
        config_path.write_text("""
feed:
  title: "Test Feed"
sources:
  - https://example.com/new1
""")
        
        json_out = temp_feed_dir / "feed.json"
        
        with patch("linkfeed.cli.process_urls") as mock_process:
            mock_process.return_value = [
                FeedItem(
                    id="new-1",
                    url="https://example.com/new1",
                    title="New Item 1",
                ),
            ]
            
            result = runner.invoke(main, [
                "--config", str(config_path),
                "--json-out", str(json_out),
            ])
        
        # Check that items were appended
        assert result.exit_code == 0
        assert "Added 1 items (total: 3)" in result.output
        
        # Verify feed contains both old and new items
        with open(json_out) as f:
            feed_data = json.load(f)
        
        assert len(feed_data["items"]) == 3

    def test_rebuild_dry_run(self, temp_feed_dir):
        """Test --rebuild with --dry-run doesn't modify feed."""
        runner = CliRunner()
        
        config_path = temp_feed_dir / "config.yaml"
        config_path.write_text("""
feed:
  title: "Test Feed"
sources:
  - https://example.com/new1
""")
        
        json_out = temp_feed_dir / "feed.json"
        
        # Read original feed
        with open(json_out) as f:
            original_data = json.load(f)
        
        with patch("linkfeed.cli.process_urls") as mock_process:
            mock_process.return_value = [
                FeedItem(
                    id="new-1",
                    url="https://example.com/new1",
                    title="New Item 1",
                ),
            ]
            
            result = runner.invoke(main, [
                "--config", str(config_path),
                "--json-out", str(json_out),
                "--rebuild",
                "--dry-run",
            ])
        
        assert result.exit_code == 0
        assert "Would rebuild feed with 1 items" in result.output
        
        # Verify feed wasn't modified
        with open(json_out) as f:
            current_data = json.load(f)
        
        assert current_data == original_data

    def test_rebuild_logs_correctly(self, temp_feed_dir, caplog):
        """Test that rebuild mode logs appropriate messages."""
        runner = CliRunner()
        
        config_path = temp_feed_dir / "config.yaml"
        config_path.write_text("""
feed:
  title: "Test Feed"
sources:
  - https://example.com/new1
""")
        
        json_out = temp_feed_dir / "feed.json"
        
        with patch("linkfeed.cli.process_urls") as mock_process:
            mock_process.return_value = [
                FeedItem(
                    id="new-1",
                    url="https://example.com/new1",
                    title="New Item 1",
                ),
            ]
            
            result = runner.invoke(main, [
                "--config", str(config_path),
                "--json-out", str(json_out),
                "--rebuild",
                "-v",  # Verbose to see log messages
            ])
        
        assert "Rebuilding feed from scratch" in result.output
