# Technology Stack

**Analysis Date:** 2026-01-25

## Languages

**Primary:**
- Python 3.8+ - Core application language, CLI implementation, feed generation, parsing, and content scraping
- Python 3.12 - Recommended development version (configured in `mise.toml`)

**Secondary:**
- HTML/CSS - Generated output for static site index (created in `linkfeed/site.py`)
- XML - RSS feed output format
- JSON - JSON Feed format and configuration

## Runtime

**Environment:**
- Python 3.8 or higher (required by pyproject.toml)
- uv - Fast Python package installer and resolver (latest version)

**Package Manager:**
- uv (universal) - Primary package manager in development
- pip - Underlying package manager (uv is wrapper)
- Lockfile: Not detected (uv uses modern approach, no lockfile required)

## Frameworks

**Core:**
- Click 8.3.1+ - CLI framework for command-line interface
- Pydantic 2.12.5+ - Data validation and settings management using Python type annotations

**Feed Generation:**
- feedgen 1.0.0 - RSS 2.0 and Atom feed generation

**Testing:**
- pytest 9.0.2+ - Test runner and framework
- pytest-cov 7.0.0+ - Code coverage reporting
- pytest-asyncio 1.3.0+ - Async test support for concurrent operations

**Content Processing:**
- BeautifulSoup 4.14.3+ - HTML parsing and web scraping
- readabilipy 0.3.0+ - Extract article content and readability scoring
- aiohttp 3.13.2+ - Async HTTP client for concurrent URL fetching

**Utilities:**
- PyYAML 6.0.3+ - YAML configuration file parsing
- python-dateutil - Date parsing and manipulation (used by openai, dateutil imports in `linkfeed/utils/date_extraction.py`)

## Key Dependencies

**Critical:**
- openai 2.14.0+ - OpenAI API client for LLM-based tag generation and date extraction. AsyncOpenAI used for concurrent processing.
- aiohttp 3.13.2+ - HTTP client essential for concurrent URL processing, web scraping, and sitemap fetching
- pydantic 2.12.5+ - Validates all configuration, models, and data structures

**Infrastructure:**
- feedgen 1.0.0 - Generates RSS feeds from parsed content
- beautifulsoup4 4.14.3+ - Parses HTML for content extraction and link discovery
- readabilipy 0.3.0+ - Extracts readable article content from web pages
- click 8.3.1+ - Provides CLI commands and option parsing

**Development:**
- pytest 9.0.2+ - Test execution and assertion framework
- pytest-asyncio 1.3.0+ - Enables async test support for concurrent operations
- pytest-cov 7.0.0+ - Measures test coverage for code quality

## Configuration

**Environment:**
- Configuration via YAML files: `linkfeed.yaml` (single feed, default) or multi-feed config format
- Site configuration: `site.yaml` (optional, for static site generation)
- Example configs: `feeds.example.yaml`, `site.example.yaml`
- Environment variables for secrets (OPENAI_API_KEY in `.env`)

**Build:**
- `pyproject.toml` - Project metadata, dependencies, scripts, pytest configuration
- `mise.toml` - Development environment: Python 3.12, uv, tasks for install/dev/test/lint/format/build
- `.github/workflows/generate-feeds.yml` - Weekly feed generation scheduled job with GitHub Pages deployment
- `.github/workflows/generate-site.yml` - Static site generation workflow

**Entry Point:**
- `linkfeed.cli:cli` - Click CLI group defined in `linkfeed/cli.py`, installed via `[project.scripts]` as `linkfeed` command

## Platform Requirements

**Development:**
- Python 3.12 (recommended via mise.toml)
- uv package manager (latest)
- Virtual environment support (.venv directory)
- POSIX shell for task execution (bash/zsh)

**Production/CI:**
- Python 3.12 (specified in GitHub Actions workflow)
- uv for dependency installation
- 10 second timeout per URL fetch (configurable via `DEFAULT_TIMEOUT` in `linkfeed/utils/network.py`)
- Concurrent request support: default 10 concurrent connections (configurable via `--concurrency` CLI option)
- GitHub Actions for automated weekly feed generation and GitHub Pages deployment

**Optional:**
- OpenAI API key for tag generation and date extraction (feature flag `--generate-tags`)

---

*Stack analysis: 2026-01-25*
