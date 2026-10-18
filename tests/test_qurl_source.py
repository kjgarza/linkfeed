"""Tests for the qurl SQLite source."""

import sqlite3

import pytest
import yaml

from linkfeed.config import load_multi_config
from linkfeed.sources import get_source
from linkfeed.sources.qurl import QurlSource


@pytest.fixture
def qurl_db(tmp_path):
    db = tmp_path / "qurl.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE documents (url TEXT, source TEXT, created_at TEXT, active INTEGER)"
    )
    conn.executemany(
        "INSERT INTO documents VALUES (?, ?, ?, ?)",
        [
            ("https://a.example/old", "readitlater", "2026-01-01 00:00:00", 1),
            ("https://a.example/new", "readitlater", "2026-10-01 00:00:00", 1),
            ("https://a.example/gone", "readitlater", "2026-05-01 00:00:00", 0),
            ("note://local", "readitlater", "2026-06-01 00:00:00", 1),
            ("https://b.example/event", "berlin-events", "2026-06-01 00:00:00", 1),
        ],
    )
    conn.commit()
    conn.close()
    return db


async def test_filters_by_source_newest_first(qurl_db):
    urls = await QurlSource(db=str(qurl_db), source="readitlater").fetch_urls()
    assert urls == ["https://a.example/new", "https://a.example/old"]


async def test_all_sources_and_limit(qurl_db):
    urls = await QurlSource(db=str(qurl_db), limit=2).fetch_urls()
    assert urls == ["https://a.example/new", "https://b.example/event"]


async def test_missing_db_returns_empty(tmp_path):
    assert await QurlSource(db=str(tmp_path / "nope.sqlite")).fetch_urls() == []


def test_db_defaults_to_env(monkeypatch, tmp_path):
    monkeypatch.setenv("QURL_DB_PATH", str(tmp_path / "env.sqlite"))
    assert QurlSource().db == tmp_path / "env.sqlite"


def test_registered():
    assert get_source("qurl") is QurlSource


def test_multi_config_parses_qurl(tmp_path):
    cfg = tmp_path / "feeds.yaml"
    cfg.write_text(yaml.safe_dump({
        "feeds": [{"name": "toreadlater", "qurl": {"source": "readitlater"}}],
    }))
    feed = load_multi_config(cfg).feeds[0]
    assert feed.qurl.source == "readitlater"
    assert feed.qurl.db is None
