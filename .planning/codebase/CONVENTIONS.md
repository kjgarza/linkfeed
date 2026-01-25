# Coding Conventions

**Analysis Date:** 2026-01-25

## Naming Patterns

**Files:**
- Module files: `snake_case.py` (e.g., `models.py`, `cli.py`, `generic.py`)
- Test files: `test_<module_name>.py` (e.g., `test_feed.py`, `test_parsers.py`, `test_utils.py`)
- Private helper functions: Prefix with underscore `_function_name` (e.g., `_scrape_website`, `_run_multi_feed`, `_get_sort_date`)

**Functions:**
- Public functions: `snake_case` (e.g., `canonicalize_url`, `generate_id`, `read_existing_feed`)
- Async functions: Same naming convention as sync functions (e.g., `async def parse(...)`, `async def process_url(...)`)
- Internal helpers: Prefix with underscore (e.g., `_get_sort_date`, `_load_site_config`, `_get_last_updated`)

**Variables:**
- Local variables: `snake_case` (e.g., `existing_feed`, `new_items`, `feed_meta`)
- Constants: `UPPER_CASE` (e.g., `TRACKING_PARAMS`, `DEFAULT_CONCURRENCY`, `XML_INVALID_CHARS`)
- Type-annotated parameters: Consistently use type hints

**Types:**
- Classes: `PascalCase` (e.g., `FeedItem`, `Feed`, `Author`, `Attachment`)
- Dataclass/Pydantic models: `PascalCase` with docstrings (e.g., `class Author(BaseModel)`)
- Type variables: `snake_case` within type hints (e.g., `Optional[str]`, `list[str]`)

## Code Style

**Formatting:**
- Tool: ruff
- Configuration: `mise.toml` defines lint and format tasks
- Run formatting: `mise format` or `python -m ruff format .`
- Run linting: `mise lint` or `python -m ruff check .`

**Linting:**
- Tool: ruff
- Standard Python linting conventions enforced via ruff
- No explicit `.ruff.toml` or similar configuration found; using ruff defaults

## Import Organization

**Order:**
1. Standard library imports (e.g., `import asyncio`, `import json`, `from datetime import datetime`)
2. Third-party imports (e.g., `import aiohttp`, `from pydantic import BaseModel`, `import click`)
3. Local application imports (e.g., `from linkfeed.models import Feed`, `from linkfeed.utils.url import canonicalize_url`)

**Example from `linkfeed/cli.py`:**
```python
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import aiohttp
import click
from openai import AsyncOpenAI

from linkfeed.config import load_config, load_multi_config
from linkfeed.feed import generate_rss, merge_feeds
from linkfeed.models import FeedItem
```

**Path Aliases:**
- No path aliases configured; uses explicit `linkfeed.` imports
- All relative imports follow absolute import style within the package

## Error Handling

**Patterns:**
- Try/except blocks with specific exception types (e.g., `except (json.JSONDecodeError, IOError) as e:`)
- Broad exception handling in async contexts with `isinstance(result, Exception)` checks
- Errors logged using logger before raising or handling
- Click CLI errors: Use `click.echo(..., err=True)` and `sys.exit(1)` for error reporting
- Configuration errors: Raise `ValueError` with descriptive messages
- Parse errors: Return `None` or `Optional[FeedItem]` rather than raising

**Example from `linkfeed/feed.py`:**
```python
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Feed.from_json_feed(data)
except (json.JSONDecodeError, IOError) as e:
    logger.warning(f"Error reading existing feed: {e}")
    return None
```

## Logging

**Framework:** Standard library `logging` module

**Module-level logger setup:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Patterns:**
- Debug logging for detailed operations: `logger.debug(f"Processing: {url}")`
- Info logging for significant actions: `logger.info(f"Parsed {len(items)} items")`
- Warning logging for recoverable issues: `logger.warning(f"Failed to fetch: {url}")`
- Error logging for exceptions with context: Log before catching non-critical exceptions
- Logging is configured in CLI via `setup_logging(verbose, quiet)` which sets level based on flags

**Example from `linkfeed/cli.py`:**
```python
def setup_logging(verbose: bool, quiet: bool) -> None:
    """Configure logging based on verbosity."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
```

## Comments

**When to Comment:**
- Module docstrings: Always include (e.g., `"""Feed generation for JSON Feed and RSS."""`)
- Class docstrings: Always include describing purpose (e.g., `"""Represents an item in the feed."""`)
- Function/method docstrings: Always include describing parameters and return value
- Inline comments: Only for non-obvious logic or business rules
- Complex regex: Explain intent (e.g., `# Regex to match XML-incompatible control characters`)

**JSDoc/TSDoc:**
- Uses Python docstrings, not JSDoc (Python project)
- Pydantic models use field descriptions implicitly via class structure
- Function docstrings are brief and focused

## Function Design

**Size:**
- Most functions are 10-50 lines
- CLI command handlers can be longer (100+ lines) due to option handling
- Helper functions are typically 5-20 lines

**Parameters:**
- Use type hints for all parameters (e.g., `path: Path`, `urls: list[str]`)
- Optional parameters use `Optional[T]` notation (e.g., `openai_client: Optional[AsyncOpenAI] = None`)
- Use dataclasses/Pydantic models for complex parameter groups rather than many individual params

**Return Values:**
- Explicit return type annotations (e.g., `-> Optional[FeedItem]`, `-> list[str]`)
- Functions that handle missing data return `None` rather than raising
- Async functions return same types as sync equivalents would

## Module Design

**Exports:**
- Core functions and classes imported directly (e.g., `from linkfeed.models import Feed, FeedItem`)
- No explicit `__all__` exports used; convention is to import what's needed
- Private implementation details use `_` prefix

**Module structure in `linkfeed/`:**
```
linkfeed/
├── models.py           # Pydantic data models
├── config.py           # Configuration loading and validation
├── feed.py             # Feed generation and I/O
├── site.py             # Site generation
├── cli.py              # CLI interface
├── parsers/
│   ├── base.py         # Abstract base class and registry
│   ├── generic.py      # Default web parser
│   ├── youtube.py      # YouTube-specific parser
│   └── media.py        # Media file parser
└── utils/
    ├── url.py          # URL utilities
    ├── network.py      # HTTP fetching
    ├── markdown.py     # Markdown scanning
    ├── scraper.py      # Website scraping
    ├── tagging.py      # Tag generation
    ├── date_extraction.py  # Date parsing
    ├── blacklist.py    # URL filtering
    ├── whitelist.py    # URL filtering
    └── trello.py       # Trello parsing
```

**Barrel Files:**
- `linkfeed/parsers/__init__.py` imports and re-exports key parsers (e.g., `from linkfeed.parsers.base import get_parser`)
- No other barrel files used; imports are explicit from source modules

---

*Convention analysis: 2026-01-25*
