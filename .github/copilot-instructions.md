# Copilot Instructions for linkfeed

## Project Overview

linkfeed is a CLI tool that converts URLs into JSON Feed v1.1 (canonical) and RSS 2.0 (derived) formats. It follows an **append-only, stateless execution model** where `feed.json` is the source of truth.

## Architecture

```
CLI (cli.py) → Config/Input Layer → Parsers → Feed Generation
     ↓              ↓                   ↓            ↓
  Click        config.py          parsers/      feed.py
              utils/markdown                   (JSON + RSS)
```

### Key Design Principles
- **JSON Feed is canonical**, RSS is derived from it via `feedgen`
- **Append-only**: New items are appended, never modify existing items
- **Deterministic IDs**: Generated from canonicalized URLs via SHA256 (see `utils/url.py`)
- **Best-effort fetching**: Parse failures log warnings but don't abort the run

## Parser System

Parsers live in `linkfeed/parsers/` and use a priority-based registry pattern:

```python
from linkfeed.parsers.base import BaseParser, register_parser

@register_parser
class MyParser(BaseParser):
    priority = 50  # Higher = tried first (GenericParser is 0)
    
    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "mysite.com" in url
    
    def parse(self, url: str, content: bytes, content_type: str | None) -> FeedItem | None:
        # Return FeedItem or None on failure
```

Existing parsers: `YouTubeParser` (priority 100), `MediaParser` (50), `GenericParser` (0 - fallback)

## Data Flow

1. URLs collected from: config YAML `sources`, CLI args, markdown files (`--from-markdown`)
2. Blacklist filtering applied (`utils/blacklist.py`) using glob patterns
3. Deduplication via `URLDeduplicator` against existing feed + current batch
4. Each URL → fetch → parser → `FeedItem`
5. `merge_feeds()` appends new items to existing `feed.json`
6. RSS regenerated from JSON Feed (sorted newest-first)

## Development Commands

```bash
# Setup (uses uv package manager)
uv pip install -e .

# Run CLI
linkfeed run --config feed-config.yaml

# Run tests
uv run pytest tests/

# Test with coverage
uv run pytest --cov=linkfeed tests/
```

## Testing Patterns

Tests use `responses` library to mock HTTP requests. See `tests/fixtures/` for sample HTML/data.

```python
# Example parser test structure
class TestMyParser:
    def test_can_handle_domain(self):
        assert MyParser.can_handle("https://mysite.com/page")
    
    def test_extracts_title(self):
        parser = MyParser()
        item = parser.parse(url, html_content, "text/html")
        assert item.title == "Expected Title"
```

## Models (Pydantic v2)

All data models are in `models.py`:
- `FeedItem`: Core item with `id`, `url`, `title`, `summary`, `tags`, `attachments`
- `Feed`: Top-level feed with `items` list and metadata
- `Attachment`: Media with `url`, `mime_type`, optional `duration_in_seconds`

Use `.to_json_feed()` / `.from_json_feed()` for serialization.

## URL Handling

`utils/url.py` handles canonicalization (removes tracking params, normalizes case/ports) and ID generation. Always use `generate_id(url)` for item IDs to ensure determinism.
