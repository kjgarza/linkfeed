# Testing Patterns

**Analysis Date:** 2026-01-25

## Test Framework

**Runner:**
- pytest 9.0.2+
- Config: `pyproject.toml` with `[tool.pytest.ini_options]`
- Async support: pytest-asyncio 1.3.0+

**Assertion Library:**
- pytest built-in assertions with `assert` keyword

**Run Commands:**
```bash
mise test                    # Run all tests with pytest
python -m pytest tests/ -v   # Run tests verbosely
python -m pytest tests/ -v --cov=linkfeed  # Run with coverage
```

**Coverage:**
```bash
python -m pytest tests/ -v --cov=linkfeed --cov-report=html
# Tools: pytest-cov 7.0.0+
# No explicit coverage requirement in config
```

## Test File Organization

**Location:**
- Test files co-located in `/Users/kristiangarza/aves/linkfeed/tests/` directory (separate from source)
- Test files parallel source module names (e.g., `test_feed.py` tests `linkfeed/feed.py`)

**Naming:**
- Test modules: `test_*.py` (e.g., `test_feed.py`, `test_parsers.py`, `test_utils.py`)
- Test classes: `Test<ModuleName>` (e.g., `TestFeedModels`, `TestMergeFeeds`, `TestParserRegistry`)
- Test methods: `test_<scenario_description>` (e.g., `test_feed_item_to_json`, `test_deduplicates`, `test_youtube_parser_priority`)

**Structure:**
```
tests/
├── __init__.py
├── fixtures/                     # Empty fixtures dir (not used currently)
├── test_feed.py                  # Feed I/O and model tests
├── test_parsers.py               # Parser registry and individual parser tests
├── test_utils.py                 # URL, Trello, tag utilities
├── test_whitelist.py             # Whitelist filtering
├── test_paragraph_selection.py   # Paragraph extraction
├── test_rebuild.py               # Feed rebuilding
└── test_site_generation.py       # Site generation
```

## Test Structure

**Suite Organization:**
```python
class TestFeedModels:
    """Logical grouping of related tests in classes."""

    def test_feed_item_to_json(self):
        """Each test method tests a specific scenario."""
        item = FeedItem(id="test-id", url="https://example.com/article")
        data = item.to_json_feed_item()
        assert data["id"] == "test-id"
```

**Patterns:**
- Setup: Use function parameters with pytest fixtures or inline object creation
- Teardown: Use `TemporaryDirectory()` context managers for file operations
- Assertion: Simple `assert condition` statements with clear expected vs actual

**Example test setup from `tests/test_feed.py`:**
```python
class TestFeedIO:
    def test_write_and_read(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "feed.json"
            feed = Feed(
                title="Test Feed",
                items=[FeedItem(id="1", url="https://example.com/1", title="One")],
            )
            write_json_feed(feed, path)
            loaded = read_existing_feed(path)
            assert loaded is not None
            assert loaded.title == "Test Feed"
```

## Async Testing

**Framework:** pytest-asyncio

**Configuration:** `asyncio_mode = "auto"` in pyproject.toml enables auto-asyncio mode

**Patterns:**
```python
@pytest.mark.asyncio
async def test_extracts_title(self):
    """Async test marked with @pytest.mark.asyncio."""
    parser = GenericParser()
    html = b"<html><head><title>Test Title</title></head></html>"
    item = await parser.parse("https://example.com", html, "text/html")
    assert item.title == "Test Title"
```

**Example from `tests/test_parsers.py`:**
```python
class TestGenericParser:
    @pytest.mark.asyncio
    async def test_extracts_og_title(self):
        parser = GenericParser()
        html = b"""
        <html>
        <head>
            <meta property="og:title" content="OG Title">
            <title>Regular Title</title>
        </head>
        </html>
        """
        item = await parser.parse("https://example.com", html, "text/html")
        assert item.title == "OG Title"
```

## Mocking

**Framework:** unittest.mock (built-in Python, used implicitly via pytest)

**What to Mock:**
- External HTTP requests (not mocked in current tests; real URLs tested)
- File I/O when testing logic (use `TemporaryDirectory()` instead)
- OpenAI API calls (not currently mocked; integration tests)

**What NOT to Mock:**
- Internal business logic (test actual functions)
- Data models and transformations
- URL parsing and canonicalization

**Patterns:**
- Tests use real URLs for parser tests: `get_parser("https://youtube.com/watch?v=abc123")`
- No monkeypatch or mock decorators found in current tests
- File operations use `tempfile.TemporaryDirectory()` for isolation

## Test Data

**Test Data Approach:**
- Inline HTML strings for HTML parsing tests
- Hardcoded URLs for URL parsing tests
- Pydantic models instantiated directly with test data

**Example from `tests/test_site_generation.py`:**
```python
def test_loads_custom_config(self, tmp_path):
    """Should load custom config from site.yaml."""
    site_yaml = tmp_path / "site.yaml"
    site_yaml.write_text("""
title: "My Custom Feeds"
description: "Personal feed collection"
""")
    config = _load_site_config(tmp_path)
    assert config.title == "My Custom Feeds"
```

**Location:**
- No separate fixture files; test data generated inline in tests
- `tests/fixtures/` directory exists but is empty

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Approach: Direct function calls with assertions
- Examples: `test_canonicalize_url`, `test_generate_id`, `test_feed_item_to_json`
- Coverage: URL utilities, data models, configuration parsing

**Integration Tests:**
- Scope: Multi-component workflows (feed generation, site generation)
- Approach: End-to-end testing with temporary files
- Examples: `test_write_and_read`, `test_merge_new_items`
- Coverage: Feed I/O, multi-feed processing

**E2E Tests:**
- Framework: Click's CliRunner
- Example from `tests/test_site_generation.py`:
```python
from click.testing import CliRunner
from linkfeed.cli import cli

runner = CliRunner()
result = runner.invoke(cli, ['generate-site'])
```

## Common Test Patterns

**Testing Optional Returns:**
```python
def test_read_nonexistent(self):
    result = read_existing_feed(Path("/nonexistent/feed.json"))
    assert result is None
```

**Testing Deduplication:**
```python
def test_deduplicates(self):
    existing = Feed(title="Test", items=[
        FeedItem(id="dup", url="https://example.com/dup", title="Original"),
    ])
    new_items = [FeedItem(id="dup", url="https://example.com/dup", title="Duplicate")]
    merged = merge_feeds(existing, new_items, {"title": "Test"})
    assert len(merged.items) == 1
    assert merged.items[0].title == "Original"
```

**Testing Parser Selection:**
```python
class TestParserRegistry:
    def test_youtube_parser_priority(self):
        parser = get_parser("https://youtube.com/watch?v=abc123")
        assert isinstance(parser, YouTubeParser)

    def test_generic_fallback(self):
        parser = get_parser("https://example.com/article")
        assert isinstance(parser, GenericParser)
```

**Testing Configuration Loading:**
```python
def test_handles_invalid_yaml(self, tmp_path):
    """Should fall back to defaults on invalid YAML."""
    site_yaml = tmp_path / "site.yaml"
    site_yaml.write_text("invalid: yaml: content: [[[")
    config = _load_site_config(tmp_path)
    # Should fall back to defaults
    assert config.title == "Feed Index"
```

**Testing List Transformations:**
```python
def test_limits_to_five(self):
    raw = "tech\nai\nscience\ndata\nml\ncloud\nweb"
    tags = parse_tags(raw)
    assert len(tags) == 5

def test_deduplicates(self):
    raw = "tech\ntech\nai\nai"
    tags = parse_tags(raw)
    assert tags == ["tech", "ai"]
```

## Test Coverage

**Current Coverage:**
- Core models: Full coverage (`test_feed.py`)
- Parsers: Good coverage of registry and basic parsing (`test_parsers.py`)
- Utilities: Comprehensive URL, Trello, tagging tests (`test_utils.py`)
- Site generation: Config loading and index generation (`test_site_generation.py`)
- Whitelist/Blacklist: Pattern matching tests (`test_whitelist.py`)

**Gaps:**
- CLI command integration tests limited
- Network error scenarios not extensively tested
- OpenAI API interactions not mocked/tested in isolation
- Markdown scanning logic not directly tested (tested via integration)

---

*Testing analysis: 2026-01-25*
