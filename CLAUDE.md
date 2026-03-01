# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**linkfeed** is a Python CLI that converts URLs into JSON Feed v1.1 (canonical) and RSS 2.0 (derived) formats. It supports multiple URL sources: direct CLI args, config YAML, markdown files, Trello board exports, and website scraping.

There is also a subpackage `packages/analysis/` — a separate Bun/TypeScript knowledge-graph extraction pipeline with its own `CLAUDE.md`.

## Commands (Python CLI)

```bash
# Setup (Python 3.12, managed by mise + uv)
uv venv && source .venv/bin/activate
uv pip install -e .          # install package
uv pip install -e '.[dev]'   # install with dev deps (pytest, pytest-cov, pytest-asyncio)

# Run
linkfeed run --config feed-config.yaml
linkfeed generate-site

# Test
uv run pytest tests/                        # all tests
uv run pytest tests/test_parsers.py         # single file
uv run pytest --cov=linkfeed tests/         # with coverage

# Lint / format (ruff, not flake8)
python -m ruff check .
python -m ruff format .
```

## Architecture

```
CLI (cli.py) → Config/Input Layer → Parsers → Feed Generation
     ↓              ↓                   ↓            ↓
  Click        config.py          parsers/      feed.py
              utils/markdown                   (JSON + RSS)
```

### Data Flow

1. URLs collected from: config YAML `sources`, CLI args, `--from-markdown`, `--from-trello`, `--website`
2. Whitelist filtering → blacklist filtering (`utils/blacklist.py`, `utils/whitelist.py`) using glob patterns
3. Deduplication via `URLDeduplicator` against existing `feed.json` + current batch (keyed by canonicalized URL hash)
4. Each URL → async fetch → parser → `FeedItem`
5. `merge_feeds()` in `feed.py` appends new items to existing `feed.json`
6. RSS is regenerated from JSON Feed (always sorted newest-first)

### Key Design Principles

- **JSON Feed is canonical**, RSS is derived from it via `feedgen`
- **Append-only by default**: existing items are never modified; `--rebuild` discards existing feed
- **Deterministic IDs**: `utils/url.py` canonicalizes URLs (strips tracking params) then SHA256-hashes them
- **Best-effort fetching**: parse failures log warnings but don't abort the run
- All network I/O is async (`aiohttp`), with a semaphore-controlled concurrency limit (default: 10)

### Parser System

Parsers live in `linkfeed/parsers/` and use a priority-based registry:

```python
from linkfeed.parsers.base import BaseParser, register_parser

@register_parser
class MyParser(BaseParser):
    priority = 50  # Higher = tried first; GenericParser is 0

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "mysite.com" in url

    def parse(self, url, content, content_type, content_length, session, openai_client) -> FeedItem | None:
        ...
```

Existing parsers: `YouTubeParser` (priority 100), `MediaParser` (50), `GenericParser` (0, fallback via readabilipy).

### Models (Pydantic v2)

All data models are in `models.py`:
- `FeedItem`: `id`, `url`, `title`, `summary`, `content_html`, `tags`, `attachments`, dates
- `Feed`: top-level with `items` list and metadata
- `Attachment`: media with `url`, `mime_type`, optional `duration_in_seconds`

Serialization: `.to_json_feed()` / `.from_json_feed()`

### Testing

Tests in `tests/`, fixtures in `tests/fixtures/`. Uses `responses` library to mock HTTP. `pytest-asyncio` is configured with `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` needed).

## Environment Variables

- `OPENAI_API_KEY` — required only for `--generate-tags` (AI tag generation via gpt-4o-mini)
