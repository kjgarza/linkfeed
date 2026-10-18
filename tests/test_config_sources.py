"""Tests for config loading with HackerNews and StackExchange sources."""

import tempfile
from pathlib import Path

import yaml

from linkfeed.config import (
    HackerNewsConfig,
    StackExchangeConfig,
    SingleFeedConfig,
    load_config,
    load_multi_config,
)


class TestHackerNewsConfig:
    def test_required_query(self):
        cfg = HackerNewsConfig(query="python async")
        assert cfg.query == "python async"

    def test_default_limit(self):
        cfg = HackerNewsConfig(query="test")
        assert cfg.limit == 20

    def test_custom_limit(self):
        cfg = HackerNewsConfig(query="test", limit=50)
        assert cfg.limit == 50


class TestStackExchangeConfig:
    def test_defaults(self):
        cfg = StackExchangeConfig()
        assert cfg.site == "stackoverflow"
        assert cfg.tagged == ""
        assert cfg.limit == 15
        assert cfg.sort == "activity"

    def test_custom_values(self):
        cfg = StackExchangeConfig(
            site="serverfault",
            tagged="linux,networking",
            limit=25,
            sort="votes",
        )
        assert cfg.site == "serverfault"
        assert cfg.tagged == "linux,networking"
        assert cfg.limit == 25
        assert cfg.sort == "votes"


class TestSingleFeedConfigDefaults:
    def test_hackernews_defaults_to_none(self):
        cfg = SingleFeedConfig()
        assert cfg.hackernews is None

    def test_stackexchange_defaults_to_none(self):
        cfg = SingleFeedConfig()
        assert cfg.stackexchange is None


class TestLoadConfigWithHN:
    def test_loads_hackernews_from_yaml(self):
        data = {
            "hackernews": {
                "query": "python async",
                "limit": 30,
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            cfg = load_config(path)
            assert cfg.hackernews is not None
            assert cfg.hackernews.query == "python async"
            assert cfg.hackernews.limit == 30
        finally:
            path.unlink()

    def test_no_hackernews_key_gives_none(self):
        data = {"sources": ["https://example.com"]}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            cfg = load_config(path)
            assert cfg.hackernews is None
        finally:
            path.unlink()


class TestLoadConfigWithSE:
    def test_loads_stackexchange_from_yaml(self):
        data = {
            "stackexchange": {
                "site": "superuser",
                "tagged": "windows",
                "limit": 10,
                "sort": "votes",
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            cfg = load_config(path)
            assert cfg.stackexchange is not None
            assert cfg.stackexchange.site == "superuser"
            assert cfg.stackexchange.tagged == "windows"
            assert cfg.stackexchange.limit == 10
            assert cfg.stackexchange.sort == "votes"
        finally:
            path.unlink()

    def test_no_stackexchange_key_gives_none(self):
        data = {"sources": ["https://example.com"]}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            cfg = load_config(path)
            assert cfg.stackexchange is None
        finally:
            path.unlink()


class TestLoadMultiConfigWithSources:
    def test_multi_config_with_hackernews(self):
        data = {
            "feeds": [
                {
                    "name": "techfeed",
                    "hackernews": {
                        "query": "rust programming",
                        "limit": 15,
                    },
                }
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            multi = load_multi_config(path)
            assert len(multi.feeds) == 1
            feed = multi.feeds[0]
            assert feed.name == "techfeed"
            assert feed.hackernews is not None
            assert feed.hackernews.query == "rust programming"
            assert feed.hackernews.limit == 15
        finally:
            path.unlink()

    def test_multi_config_with_stackexchange(self):
        data = {
            "feeds": [
                {
                    "name": "devfeed",
                    "stackexchange": {
                        "site": "stackoverflow",
                        "tagged": "python,asyncio",
                        "limit": 20,
                    },
                }
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            multi = load_multi_config(path)
            feed = multi.feeds[0]
            assert feed.stackexchange is not None
            assert feed.stackexchange.site == "stackoverflow"
            assert feed.stackexchange.tagged == "python,asyncio"
        finally:
            path.unlink()

    def test_multi_config_without_sources_defaults_to_none(self):
        data = {
            "feeds": [
                {
                    "name": "simple",
                    "sources": ["https://example.com"],
                }
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            multi = load_multi_config(path)
            feed = multi.feeds[0]
            assert feed.hackernews is None
            assert feed.stackexchange is None
        finally:
            path.unlink()

    def test_multi_config_with_both_sources(self):
        data = {
            "feeds": [
                {
                    "name": "techfeed",
                    "hackernews": {"query": "python async"},
                    "stackexchange": {"site": "stackoverflow", "tagged": "python"},
                }
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = Path(f.name)

        try:
            multi = load_multi_config(path)
            feed = multi.feeds[0]
            assert feed.hackernews is not None
            assert feed.stackexchange is not None
            assert feed.hackernews.query == "python async"
            assert feed.stackexchange.site == "stackoverflow"
        finally:
            path.unlink()
