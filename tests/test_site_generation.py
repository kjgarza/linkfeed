"""Tests for site generation functionality."""

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from linkfeed.cli import cli
from linkfeed.models import Feed, FeedItem
from linkfeed.site import _load_site_config, _get_last_updated, SiteConfig


class TestLoadSiteConfig:
    """Test site.yaml configuration loading."""

    def test_returns_defaults_when_no_config(self, tmp_path):
        """Should return default config when site.yaml doesn't exist."""
        config = _load_site_config(tmp_path)
        
        assert config.title == "Feed Index"
        assert config.description == "A collection of RSS and JSON feeds"

    def test_loads_custom_config(self, tmp_path):
        """Should load custom config from site.yaml."""
        site_yaml = tmp_path / "site.yaml"
        site_yaml.write_text("""
title: "My Custom Feeds"
description: "Personal feed collection"
""")
        
        config = _load_site_config(tmp_path)
        
        assert config.title == "My Custom Feeds"
        assert config.description == "Personal feed collection"

    def test_handles_partial_config(self, tmp_path):
        """Should use defaults for missing fields."""
        site_yaml = tmp_path / "site.yaml"
        site_yaml.write_text("title: 'Just a title'\n")
        
        config = _load_site_config(tmp_path)
        
        assert config.title == "Just a title"
        assert config.description == "A collection of RSS and JSON feeds"

    def test_handles_invalid_yaml(self, tmp_path):
        """Should fall back to defaults on invalid YAML."""
        site_yaml = tmp_path / "site.yaml"
        site_yaml.write_text("invalid: yaml: content: [[[")
        
        config = _load_site_config(tmp_path)
        
        # Should fall back to defaults
        assert config.title == "Feed Index"

    def test_handles_empty_file(self, tmp_path):
        """Should handle empty site.yaml."""
        site_yaml = tmp_path / "site.yaml"
        site_yaml.write_text("")
        
        config = _load_site_config(tmp_path)
        
        assert config.title == "Feed Index"


class TestGetLastUpdated:
    """Test the _get_last_updated function."""

    def test_handles_timezone_aware_dates(self):
        """Should handle timezone-aware ISO dates."""
        items = [
            {"date_published": "2024-01-01T10:00:00+00:00"},
            {"date_published": "2024-01-15T12:00:00+00:00"},
            {"date_published": "2024-01-10T08:00:00+00:00"},
        ]
        
        result = _get_last_updated(items)
        
        assert result == "2024-01-15"

    def test_handles_timezone_naive_dates(self):
        """Should handle timezone-naive ISO dates."""
        items = [
            {"date_published": "2024-01-01T10:00:00"},
            {"date_published": "2024-01-15T12:00:00"},
            {"date_published": "2024-01-10T08:00:00"},
        ]
        
        result = _get_last_updated(items)
        
        assert result == "2024-01-15"

    def test_handles_mixed_timezone_dates(self):
        """Should handle mix of timezone-aware and naive dates."""
        items = [
            {"date_published": "2024-01-01T10:00:00"},  # naive
            {"date_published": "2024-01-15T12:00:00+00:00"},  # aware
            {"date_published": "2024-01-10T08:00:00"},  # naive
        ]
        
        # Should not raise "can't compare offset-naive and offset-aware datetimes"
        result = _get_last_updated(items)
        
        assert result == "2024-01-15"

    def test_handles_z_suffix(self):
        """Should handle Z suffix for UTC."""
        items = [
            {"date_published": "2024-01-01T10:00:00Z"},
            {"date_published": "2024-01-15T12:00:00Z"},
        ]
        
        result = _get_last_updated(items)
        
        assert result == "2024-01-15"

    def test_handles_date_modified_fallback(self):
        """Should fall back to date_modified if no date_published."""
        items = [
            {"date_modified": "2024-01-01T10:00:00Z"},
            {"date_published": "2024-01-15T12:00:00Z"},
        ]
        
        result = _get_last_updated(items)
        
        assert result == "2024-01-15"

    def test_returns_unknown_for_empty_items(self):
        """Should return 'Unknown' for empty items list."""
        assert _get_last_updated([]) == "Unknown"

    def test_returns_unknown_for_invalid_dates(self):
        """Should return 'Unknown' if all dates are invalid."""
        items = [
            {"date_published": "invalid"},
            {"date_published": "also-invalid"},
        ]
        
        assert _get_last_updated(items) == "Unknown"

    def test_ignores_invalid_dates_but_uses_valid(self):
        """Should ignore invalid dates but use valid ones."""
        items = [
            {"date_published": "invalid"},
            {"date_published": "2024-01-15T12:00:00Z"},
            {"date_published": "also-invalid"},
        ]
        
        result = _get_last_updated(items)
        
        assert result == "2024-01-15"


class TestGenerateSiteCommand:
    """Test the generate-site CLI command."""

    def test_generates_site_with_defaults(self, tmp_path):
        """Should generate site with default settings."""
        feeds_dir = tmp_path / "feeds"
        feeds_dir.mkdir()
        
        # Create a sample feed
        feed_dir = feeds_dir / "test-feed"
        feed_dir.mkdir()
        feed_json = feed_dir / "feed.json"
        
        feed = Feed(
            version="https://jsonfeed.org/version/1.1",
            title="Test Feed",
            home_page_url="https://example.com",
            description="A test feed",
            items=[
                FeedItem(
                    id="item-1",
                    url="https://example.com/1",
                    title="Test Item",
                )
            ],
        )
        
        with open(feed_json, "w") as f:
            json.dump(feed.to_json_feed(), f)
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate-site",
            "--feeds-dir", str(feeds_dir),
        ])
        
        assert result.exit_code == 0
        assert "Generated site index" in result.output
        
        # Check index.html was created
        index_path = feeds_dir / "index.html"
        assert index_path.exists()
        
        html = index_path.read_text()
        assert "Test Feed" in html
        assert "A test feed" in html

    def test_uses_site_yaml_config(self, tmp_path):
        """Should use site.yaml configuration."""
        feeds_dir = tmp_path / "feeds"
        feeds_dir.mkdir()
        
        # Create site.yaml
        site_yaml = feeds_dir / "site.yaml"
        site_yaml.write_text("""
title: "Custom Title"
description: "Custom Description"
""")
        
        # Create minimal feed
        feed_dir = feeds_dir / "test"
        feed_dir.mkdir()
        (feed_dir / "feed.json").write_text('{"version": "https://jsonfeed.org/version/1.1", "title": "Test", "items": []}')
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate-site",
            "--feeds-dir", str(feeds_dir),
        ])
        
        assert result.exit_code == 0
        
        html = (feeds_dir / "index.html").read_text()
        assert "Custom Title" in html
        assert "Custom Description" in html

    def test_cli_args_override_config(self, tmp_path):
        """CLI arguments should override site.yaml."""
        feeds_dir = tmp_path / "feeds"
        feeds_dir.mkdir()
        
        # Create site.yaml
        site_yaml = feeds_dir / "site.yaml"
        site_yaml.write_text("""
title: "Config Title"
description: "Config Description"
""")
        
        # Create minimal feed
        feed_dir = feeds_dir / "test"
        feed_dir.mkdir()
        (feed_dir / "feed.json").write_text('{"version": "https://jsonfeed.org/version/1.1", "title": "Test", "items": []}')
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate-site",
            "--feeds-dir", str(feeds_dir),
            "--title", "CLI Title",
            "--description", "CLI Description",
        ])
        
        assert result.exit_code == 0
        
        html = (feeds_dir / "index.html").read_text()
        assert "CLI Title" in html
        assert "CLI Description" in html
        assert "Config Title" not in html

    def test_custom_output_path(self, tmp_path):
        """Should respect custom output path."""
        feeds_dir = tmp_path / "feeds"
        feeds_dir.mkdir()
        custom_output = tmp_path / "custom" / "index.html"
        
        # Create minimal feed
        feed_dir = feeds_dir / "test"
        feed_dir.mkdir()
        (feed_dir / "feed.json").write_text('{"version": "https://jsonfeed.org/version/1.1", "title": "Test", "items": []}')
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate-site",
            "--feeds-dir", str(feeds_dir),
            "--output", str(custom_output),
        ])
        
        assert result.exit_code == 0
        assert custom_output.exists()

    def test_handles_no_feeds(self, tmp_path):
        """Should handle directory with no feeds."""
        feeds_dir = tmp_path / "empty-feeds"
        feeds_dir.mkdir()
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate-site",
            "--feeds-dir", str(feeds_dir),
        ])
        
        assert result.exit_code == 0
        
        html = (feeds_dir / "index.html").read_text()
        assert "No feeds found" in html

    def test_scans_nested_directories(self, tmp_path):
        """Should find feeds in nested directories."""
        feeds_dir = tmp_path / "feeds"
        feeds_dir.mkdir()
        
        # Create nested feed structure
        nested_dir = feeds_dir / "category" / "subcategory"
        nested_dir.mkdir(parents=True)
        
        feed = Feed(
            version="https://jsonfeed.org/version/1.1",
            title="Nested Feed",
            items=[],
        )
        
        with open(nested_dir / "feed.json", "w") as f:
            json.dump(feed.to_json_feed(), f)
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate-site",
            "--feeds-dir", str(feeds_dir),
        ])
        
        assert result.exit_code == 0
        
        html = (feeds_dir / "index.html").read_text()
        assert "Nested Feed" in html
