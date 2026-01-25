# Codebase Structure

**Analysis Date:** 2026-01-25

## Directory Layout

```
linkfeed/
├── linkfeed/                    # Main package directory
│   ├── __init__.py              # Package initialization, __version__ = "0.1.0"
│   ├── cli.py                   # CLI commands and orchestration
│   ├── config.py                # Configuration loading and validation
│   ├── models.py                # Pydantic data models
│   ├── feed.py                  # Feed generation (JSON Feed, RSS)
│   ├── site.py                  # Static site generation
│   ├── parsers/                 # Pluggable content parsers
│   │   ├── __init__.py
│   │   ├── base.py              # BaseParser ABC and registry pattern
│   │   ├── generic.py           # HTML content extraction (ReadabiliPy)
│   │   ├── youtube.py           # YouTube-specific metadata extraction
│   │   └── media.py             # Media attachment extraction
│   └── utils/                   # Reusable utility functions
│       ├── __init__.py
│       ├── blacklist.py         # Domain/URL blacklist filtering
│       ├── whitelist.py         # Domain/URL whitelist filtering
│       ├── url.py               # URL canonicalization, ID generation, deduplication
│       ├── network.py           # Async HTTP fetching with aiohttp
│       ├── scraper.py           # Website link scraping
│       ├── markdown.py          # Markdown file URL extraction
│       ├── trello.py            # Trello board JSON parsing
│       ├── tagging.py           # OpenAI-based tag generation
│       └── date_extraction.py   # Publication date extraction from HTML
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_feed.py             # Feed merging, serialization
│   ├── test_parsers.py          # Parser functionality
│   ├── test_utils.py            # URL, filtering, date utilities
│   ├── test_site_generation.py  # Site index generation
│   ├── test_whitelist.py        # Whitelist filtering
│   ├── test_rebuild.py          # Feed rebuild functionality
│   ├── test_paragraph_selection.py # Content extraction tests
│   └── fixtures/                # Test data files
├── feeds/                       # Generated feed output directory (runtime)
│   ├── index.html               # Multi-feed site index
│   └── {feed_name}/             # Per-feed subdirectories
│       ├── feed.json            # JSON Feed v1.1 output
│       ├── feed.xml             # RSS 2.0 output
│       └── site.yaml            # Feed-specific site config (optional)
├── docs/                        # Documentation and planning
│   ├── plan.md
│   ├── plan-opus.md
│   └── plan-multiFeedStaticSite.prompt.md
├── .github/workflows/           # GitHub Actions workflows
│   ├── generate-feeds.yml       # Scheduled feed generation
│   └── generate-site.yml        # Site generation workflow (uncommitted)
├── .planning/                   # GSD planning documents
│   └── codebase/                # Architecture analysis (this file)
├── pyproject.toml               # Python project metadata and dependencies
├── LICENSE                      # MIT License
├── README.md                    # Project documentation
├── linkfeed.yaml                # Single-feed config example
├── feed-config.yaml             # Alternative feed config example
├── feeds.example.yaml           # Multi-feed config example
├── site.example.yaml            # Site config example
├── mise.toml                    # Tool version management
├── CITATION.cff                 # Citation metadata
└── .env                         # Environment variables (secrets, not committed)
```

## Directory Purposes

**linkfeed/:**
- Purpose: Main Python package containing all source code
- Contains: CLI, models, parsers, utilities, feed generation logic
- Key files: `cli.py` (entry point), `models.py` (data models), `feed.py` (output generation)

**linkfeed/parsers/:**
- Purpose: Pluggable parser system for extracting content from different URL types
- Contains: BaseParser base class, registry pattern, specialized parsers
- Key files: `base.py` (registry), `generic.py` (HTML fallback), `youtube.py` (video metadata)

**linkfeed/utils/:**
- Purpose: Reusable utility functions for URL, network, content processing
- Contains: Filtering (whitelist/blacklist), URL utilities, async network, scraping, extraction
- Key files: `url.py` (canonicalization), `network.py` (HTTP), `whitelist.py`/`blacklist.py` (filtering)

**tests/:**
- Purpose: Pytest-based test suite with async support
- Contains: Unit tests for models, parsers, utilities, feed I/O, site generation
- Key files: `test_feed.py`, `test_parsers.py`, `test_utils.py`
- Config: `pytest.ini_options` in pyproject.toml with asyncio_mode="auto"

**feeds/:**
- Purpose: Runtime output directory for generated feeds
- Contains: feed.json (JSON Feed), feed.xml (RSS), index.html (multi-feed index)
- Generated: Yes (not committed to git, created by CLI)
- Committed: No (feeds/ in .gitignore)

**docs/:**
- Purpose: Documentation and planning notes
- Contains: Project plans, implementation notes, design decisions
- Committed: Yes

**.github/workflows/:**
- Purpose: GitHub Actions CI/CD automation
- Contains: Scheduled feed generation, site generation workflows
- Key files: `generate-feeds.yml` (weekly cron), `generate-site.yml` (uncommitted)

**.planning/codebase/:**
- Purpose: GSD codebase analysis and architecture documentation
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md, STACK.md, INTEGRATIONS.md
- Committed: Yes

## Key File Locations

**Entry Points:**

- `linkfeed/cli.py`: Main CLI using Click framework with `@click.group()` and `@cli.command()` decorators
  - Command: `run` - Generate feeds from URL sources
  - Command: `generate-site` - Generate static index.html
- `pyproject.toml`: Defines `linkfeed = "linkfeed.cli:cli"` as console script entry point

**Configuration:**

- `linkfeed/config.py`: Load and validate YAML configs (SingleFeedConfig, MultiConfig)
- `linkfeed.yaml`: Single-feed configuration template
- `feeds.example.yaml`: Multi-feed configuration template
- `site.example.yaml`: Site index configuration template

**Core Logic:**

- `linkfeed/models.py`: Pydantic data models (Feed, FeedItem, Author, Attachment)
- `linkfeed/feed.py`: Feed merging, JSON Feed/RSS serialization
- `linkfeed/site.py`: Static site index generation from feed.json files
- `linkfeed/parsers/base.py`: Parser registry and abstract base class
- `linkfeed/utils/url.py`: URL canonicalization and ID generation (SHA256)

**Testing:**

- `tests/`: Pytest suite with fixtures/ subdirectory
- `pyproject.toml`: Pytest configuration under [tool.pytest.ini_options]
- Run tests: `pytest` or `pytest -v` or `pytest --cov`

## Naming Conventions

**Files:**

- Python modules: `snake_case.py` (e.g., `generic.py`, `date_extraction.py`)
- Configuration files: lowercase with hyphens (e.g., `feed-config.yaml`)
- Test files: `test_*.py` (e.g., `test_feed.py`, `test_utils.py`)
- Config templates: `*.example.yaml` (e.g., `feeds.example.yaml`)

**Directories:**

- Python packages: `snake_case` (e.g., `linkfeed`, `utils`, `parsers`)
- Output directories: lowercase (e.g., `feeds`, `tests`, `docs`)
- Generated content: No special naming (feed.json, feed.xml, index.html)

**Python Code:**

- Classes: `PascalCase` (e.g., `FeedItem`, `GenericParser`, `URLDeduplicator`)
- Functions/methods: `snake_case` (e.g., `parse_tags`, `filter_blacklisted`, `generate_id`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONCURRENCY`, `TRACKING_PARAMS`, `TAG_PROMPT`)
- Private/internal: `_snake_case` (e.g., `_parse_feed_data`, `_get_last_updated`, `_escape_html`)
- Type hints: Always present in function signatures

**Pydantic Models:**

- Configuration models: `*Config` suffix (e.g., `FeedConfig`, `SiteConfig`)
- Data models: No suffix (e.g., `Feed`, `FeedItem`, `Author`, `Attachment`)

## Where to Add New Code

**New Feature:**

- **Primary code:** Implement in `linkfeed/{module}.py` or `linkfeed/{package}/` subdirectory
  - Example: New content parser → `linkfeed/parsers/custom.py`
  - Example: New URL source → `linkfeed/utils/new_source.py`
- **Tests:** Create `tests/test_{module}.py` or add to existing test file
  - Pattern: Mirror package structure (test file per source module)
- **Configuration:** Add Pydantic model to `linkfeed/config.py` if new config needed
- **CLI:** Modify `linkfeed/cli.py` to expose feature via new command or option
  - Use `@cli.command()` decorator for new commands
  - Use `@click.option()` decorators for command arguments

**New Component/Module:**

- **Implementation:** Create `linkfeed/{component_name}.py` or `linkfeed/{category}/{component_name}.py`
  - Existing categories: `parsers/`, `utils/`
  - Pattern: One main class or set of functions per module
- **Exports:** Re-export from `linkfeed/` package level if widely used
  - Location: `linkfeed/__init__.py` (currently only exports __version__)
- **Tests:** `tests/test_{component_name}.py` using pytest class-based organization
  - Pattern: Use pytest fixtures from conftest.py if needed (create if missing)

**Utilities:**

- **Shared helpers:** Add to `linkfeed/utils/{helper_name}.py`
  - Naming: Group related functions in a single module (e.g., all URL utilities in `url.py`)
  - Pattern: Export all public functions, prefix internal functions with `_`
- **Parsers:** Extend `linkfeed/parsers/{type}.py` (inherit from BaseParser, register decorator)
  - Pattern: Implement `can_handle(url)` for URL matching, `parse()` for async extraction
  - Registration: Decorate class with `@register_parser`

**Configuration:**

- **New config option:** Add field to appropriate Pydantic model in `linkfeed/config.py`
  - For single-feed: Add to `SingleFeedConfig`
  - For multi-feed: Add to `NamedFeedConfig` or `MultiConfig`
  - For site: Add to `SiteConfig` in `linkfeed/site.py`
- **YAML examples:** Update `linkfeed.yaml`, `feeds.example.yaml`, `site.example.yaml`

## Special Directories

**feeds/:**
- Purpose: Runtime output directory for generated feed files
- Generated: Yes (created during `linkfeed run` execution)
- Committed: No (all feeds/ content in .gitignore)
- Cleanup: Safe to delete; regenerate with `linkfeed run`

**tests/fixtures/:**
- Purpose: Test data files (HTML samples, JSON samples, etc.)
- Generated: No (manually created test data)
- Committed: Yes
- Usage: Loaded by test files for deterministic testing

**.pytest_cache/:**
- Purpose: Pytest cache for test collection
- Generated: Yes (auto-created by pytest)
- Committed: No (.gitignore)

**.venv/:**
- Purpose: Python virtual environment
- Generated: Yes (created by `uv venv` or `python -m venv`)
- Committed: No (.gitignore)

**.git/:**
- Purpose: Git repository metadata
- Generated: Yes (created by `git init`)
- Committed: Always

**.planning/:**
- Purpose: GSD (Genie Software Development) planning documents
- Generated: No (manually created architecture analysis)
- Committed: Yes
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md, STACK.md, INTEGRATIONS.md

---

*Structure analysis: 2026-01-25*
