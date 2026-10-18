# Plan: Tiered Fallback Fetching + HN/SE Source Types

## Context

Many URLs silently fail in linkfeed because sites block direct HTTP scraping (403, Cloudflare, JS-rendered content). The current `fetch_url()` in `utils/network.py` makes a single aiohttp GET and returns `None` on failure. Additionally, there's no way to discover URLs from HackerNews or StackExchange — these would be valuable new source types alongside the existing markdown/trello/website sources.

**Goal:** (1) Add Jina Reader as a fallback when direct HTTP fails, (2) Add HN and SE as new URL source types configurable via YAML and CLI.

---

## Part 1: Tiered Fallback Fetching

**File: `linkfeed/utils/network.py`**

Refactor `fetch_url()` into a tiered strategy:

1. **`_fetch_direct()`** — extract current aiohttp GET logic, but return result even on error status (don't `raise_for_status()`) so caller can inspect status code
2. **`_fetch_with_backoff()`** — wrap `_fetch_direct()` with exponential backoff on 429 (2s base, max 3 retries)
3. **`_should_fallback()`** — returns True for: None result, 403, 429, 5xx, empty content
4. **`_fetch_jina()`** — GET `https://r.jina.ai/{url}`, returns markdown content, uses `JINA_API_KEY` env var if set
5. **`fetch_url()`** — orchestrator: `_fetch_with_backoff()` → if `_should_fallback()` → `_fetch_jina()`

Add `fetched_via: str` field to `FetchResult` dataclass ("direct" or "jina"). Add `enable_fallback: bool = True` param to `fetch_url()`.

**Parsers remain unchanged** — they receive `FetchResult` as before. Jina returns markdown which will flow through GenericParser's BeautifulSoup fallback path (acceptable for now).

---

## Part 2: New Source Types (HN, SE)

### New module: `linkfeed/sources/`

| File | Purpose |
|------|---------|
| `sources/base.py` | `BaseSource` ABC + `register_source()` / `get_source()` registry (same pattern as `parsers/base.py`) |
| `sources/hackernews.py` | `HackerNewsSource` — Algolia API (`hn.algolia.com/api/v1/search`), returns URL list. Filters `tags=story`, skips null URLs (Ask HN posts) |
| `sources/stackexchange.py` | `StackExchangeSource` — SE API v2.3 (`api.stackexchange.com/2.3/questions`), returns question URLs. Unauthenticated, 300 req/day/IP |
| `sources/__init__.py` | Registry imports |

### Config changes: `linkfeed/config.py`

Add Pydantic models:
- `HackerNewsConfig(query: str, limit: int = 20)`
- `StackExchangeConfig(site: str = "stackoverflow", tagged: str = "", limit: int = 15, sort: str = "activity")`

Add `hackernews: Optional[HackerNewsConfig]` and `stackexchange: Optional[StackExchangeConfig]` to both `SingleFeedConfig` and `NamedFeedConfig`. Update `load_config()` and `load_multi_config()` to parse these keys.

**YAML format:**
```yaml
feeds:
  - name: techfeed
    hackernews:
      query: "python async"
      limit: 20
    stackexchange:
      site: stackoverflow
      tagged: "python,asyncio"
      limit: 15
```

### CLI changes: `linkfeed/cli.py`

Add flags to `run` command:
- `--from-hackernews "query"` — search HN via Algolia
- `--from-stackexchange "site:tag1,tag2"` — fetch SE questions

Add URL collection blocks after the website scraping section, both for CLI flags and config sources. Same pattern in `_run_multi_feed()`.

---

## Part 3: Tests

**New dev dependency:** `aioresponses>=0.7.6` (for mocking aiohttp, since `responses` is for `requests`)

| Test file | Covers |
|-----------|--------|
| `tests/test_network.py` | `_should_fallback()`, direct success, 403→Jina fallback, timeout→fallback, both-fail→None, fallback disabled, 429 backoff retries |
| `tests/test_sources.py` | Source registry, HN returns/filters URLs, HN respects limit, HN API error, SE returns URLs, SE API error |
| `tests/test_config_sources.py` | Config loading with HN/SE, defaults to None, multi-config with sources |

Monkeypatch `asyncio.sleep` in backoff tests to avoid delays.

---

## Implementation Order

1. `pyproject.toml` — add `aioresponses` dev dep
2. `linkfeed/utils/network.py` — tiered fallback refactor
3. `tests/test_network.py` — fallback tests
4. `linkfeed/sources/base.py` — BaseSource + registry
5. `linkfeed/sources/hackernews.py` — HN source
6. `linkfeed/sources/stackexchange.py` — SE source
7. `linkfeed/sources/__init__.py` — registry exports
8. `tests/test_sources.py` — source tests
9. `linkfeed/config.py` — new config models + loader updates
10. `tests/test_config_sources.py` — config tests
11. `linkfeed/cli.py` — CLI flags + URL collection integration

---

## Verification

1. `uv pip install -e '.[dev]'` — install with new dep
2. `uv run pytest tests/test_network.py -v` — fallback tests pass
3. `uv run pytest tests/test_sources.py -v` — source tests pass
4. `uv run pytest tests/test_config_sources.py -v` — config tests pass
5. `uv run pytest tests/ -v` — all tests pass (no regressions)
6. `python -m ruff check .` — lint clean
7. Manual smoke test: `linkfeed run --from-hackernews "python" --output-dir /tmp/hn-test` — produces feed with HN URLs
