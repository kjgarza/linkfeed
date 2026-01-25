# External Integrations

**Analysis Date:** 2026-01-25

## APIs & External Services

**OpenAI API:**
- Service: LLM-based tag generation and date extraction from articles
- What it's used for: Generate 3-5 topic tags from article content, extract publication dates from article text
- SDK/Client: `openai` 2.14.0+ package, specifically `AsyncOpenAI` for concurrent processing
- Auth: Environment variable `OPENAI_API_KEY` (see `.env`)
- Model: `gpt-4o-mini` by default (configurable via `--openai-model` CLI flag)
- Activation: Optional feature via `--generate-tags` CLI flag or workflow input
- Implementation: `linkfeed/utils/tagging.py` (tag generation), `linkfeed/utils/date_extraction.py` (date extraction)
- Max tokens: 100 tokens per completion request
- Temperature: 0.3 (low, for consistent outputs)

## Data Storage

**Databases:**
- None. Application is stateless feed generator.

**File Storage:**
- Local filesystem only
- Output paths:
  - JSON Feed: `feed.json` (default output or `--json-out` option)
  - RSS Feed: `feed.xml` (default output or `--rss-out` option)
  - Static site index: `feeds/index.html` (or custom via `--output` option)
- Config files: YAML format in project root (`linkfeed.yaml`, `claude-feed.yaml`, etc.)
- Feed data directory: `feeds/` (default, configurable via `--feeds-dir`)

**Caching:**
- URL deduplication in memory using `URLDeduplicator` class (`linkfeed/utils/url.py`)
- Existing feed reading for incremental updates: reads previous `feed.json` to avoid re-processing URLs
- HTTP connection pooling: aiohttp TCPConnector with 100 total connections, 10 per-host limit

## Authentication & Identity

**Auth Provider:**
- None for feed sources. All public URLs fetched via HTTP(S).
- OpenAI authentication only: API key in environment variable `OPENAI_API_KEY`

**Custom Implementation:**
- OpenAI client initialization: `create_openai_client()` in `linkfeed/utils/tagging.py`
- Falls back gracefully if API key missing (logs error, disables tag generation)

## Content Sources

**URL Sources:**
Multiple input methods supported via CLI:
1. Direct URLs as CLI arguments
2. YAML config files (sources list)
3. Markdown directory scanning: extract URLs from markdown files
4. Website scraping: crawl sitemap.xml or page links
5. Trello board JSON export: parse cards for URLs

**Content Fetching:**
- HTTP(S) via `aiohttp` 3.13.2+
- User-Agent: `linkfeed/0.1.0 (+https://github.com/linkfeed)`
- Timeout: 10 seconds per request (configurable)
- Redirects: Follow up to 5 redirects
- Connection pooling: 100 total / 10 per-host

**Web Scraping:**
- HTML parsing: BeautifulSoup 4.14.3+ with html.parser backend
- Sitemap discovery: Attempts `/sitemap.xml`, `/sitemap_index.xml`, `/sitemap-index.xml`
- Article selectors: `article`, `main`, `.post`, `.entry`, `.article`, `.content` elements
- Same-domain filtering: Only links from same domain included
- Link filtering: Excludes navigation, assets, auth pages, feeds

## Monitoring & Observability

**Error Tracking:**
- None (no external service)

**Logs:**
- Python logging module (stdlib)
- Log output to stdout/stderr
- Levels: DEBUG, INFO, WARNING, ERROR
- Configurable via `--verbose` (DEBUG), default (INFO), `--quiet` (ERROR)
- Format: "%(levelname)s: %(message)s"

## CI/CD & Deployment

**Hosting:**
- GitHub Pages for generated feeds and static site index
- Source: GitHub repository (kjgarza/linkfeed)

**CI Pipeline:**
- GitHub Actions
- Workflows:
  - `.github/workflows/generate-feeds.yml` - Weekly schedule (Sunday midnight UTC) + manual dispatch
  - `.github/workflows/generate-site.yml` - Static site generation
- Python 3.12 setup via actions/setup-python@v5
- uv setup via astral-sh/setup-uv@v4
- Artifacts: Uploaded to GitHub Pages via actions/upload-pages-artifact@v3
- Deployment: actions/deploy-pages@v4

## Environment Configuration

**Required env vars:**
- `OPENAI_API_KEY` - For tag generation feature (optional, gracefully skipped if missing)

**Optional env vars:**
- None detected currently (configuration primarily via YAML and CLI flags)

**Secrets location:**
- `.env` file (local development only, not committed)
- GitHub Secrets for CI: `OPENAI_API_KEY` referenced in workflow as `${{ secrets.OPENAI_API_KEY }}`

## Configuration Files

**Feed Configuration (YAML):**

Single feed format (`linkfeed.yaml`):
```yaml
feed:
  title: "Feed Title"
  home_page_url: "https://example.com"
  feed_url: "https://example.com/feed.json"
  description: "Feed description"
  language: "en"

sources:
  - https://example.com/article1
  - https://example.com/article2

whitelist:
  - "example.com/*"

blacklist:
  - "*.pdf"
  - "*/login"

markdown_dir: "./my-bookmarks"
website: "https://example.com/blog"

trello:
  file: "trello-export.json"
  lists:
    - "list-id-1"
    - "list-id-2"
```

Multi-feed format (`claude-feed.yaml`):
```yaml
global_whitelist:
  - "*.com"

global_blacklist:
  - "*.pdf"

feeds:
  - name: "feed1"
    feed:
      title: "Feed 1"
    sources: [...]
    output_dir: "custom-output"
```

Site configuration (`site.yaml`):
```yaml
title: "My Feeds"
description: "Personal feed collection"
```

## Webhooks & Callbacks

**Incoming:**
- None (application is pull-only)

**Outgoing:**
- GitHub Pages deployment notifications (automatic after workflow completes)
- No custom webhooks

---

*Integration audit: 2026-01-25*
