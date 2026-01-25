# Architecture

**Analysis Date:** 2026-01-25

## Pattern Overview

**Overall:** URL Aggregation and Feed Generation Pipeline

**Key Characteristics:**
- Command-driven CLI architecture for multiple feed generation workflows
- Multi-source URL collection (direct URLs, markdown files, Trello boards, website scraping)
- Pluggable parser system for specialized content extraction (YouTube, media, generic HTML)
- Async/concurrent URL processing with semaphore-based rate limiting
- Feed format generation (JSON Feed v1.1 and RSS 2.0)
- Optional LLM-based content tagging (OpenAI)

## Layers

**CLI Layer:**
- Purpose: Command-line interface and argument parsing for all user interactions
- Location: `linkfeed/cli.py`
- Contains: Click-based command groups (`run`, `generate-site`), async orchestration, logging setup
- Depends on: config, feed, parsers, utils (all modules)
- Used by: End users and CI/CD workflows

**Configuration Layer:**
- Purpose: Load and validate feed configurations from YAML files
- Location: `linkfeed/config.py`
- Contains: Pydantic models for SingleFeedConfig, MultiConfig, NamedFeedConfig, TrelloSource, FeedConfig
- Depends on: pydantic, yaml
- Used by: CLI layer to bootstrap feed settings

**Data Model Layer:**
- Purpose: Define core data structures for feeds and items
- Location: `linkfeed/models.py`
- Contains: Feed, FeedItem, Author, Attachment Pydantic models with JSON Feed serialization
- Depends on: pydantic
- Used by: Parser layer, feed generation layer, CLI layer

**Parser Layer:**
- Purpose: Extract structured metadata from URLs (title, summary, content, authors, dates)
- Location: `linkfeed/parsers/` (base.py, generic.py, youtube.py, media.py)
- Contains: BaseParser abstract class with registry pattern; specialized parsers for YouTube, media attachments, generic HTML with ReadabiliPy
- Depends on: models, utils (date_extraction, url), beautifulsoup4, readabilipy, dateutil
- Used by: CLI layer (via get_parser)

**Feed Generation Layer:**
- Purpose: Merge parsed items with existing feeds and output standardized formats
- Location: `linkfeed/feed.py`
- Contains: read_existing_feed, write_json_feed, merge_feeds, generate_rss functions
- Depends on: models, feedgen, json, xml sanitization
- Used by: CLI layer

**Site Generation Layer:**
- Purpose: Generate static HTML index page listing all feeds
- Location: `linkfeed/site.py`
- Contains: generate_index_html function, HTML template, SiteConfig model for site.yaml
- Depends on: models, yaml, json, html escaping
- Used by: CLI layer (generate-site command)

**URL Collection Layer:**
- Purpose: Gather URLs from various sources
- Location: `linkfeed/utils/markdown.py`, `linkfeed/utils/scraper.py`, `linkfeed/utils/trello.py`
- Contains: scan_markdown_directory, scrape_website_links, parse_trello_board
- Depends on: aiohttp, BeautifulSoup4
- Used by: CLI layer

**URL Filtering Layer:**
- Purpose: Apply whitelist and blacklist patterns to URLs
- Location: `linkfeed/utils/whitelist.py`, `linkfeed/utils/blacklist.py`
- Contains: matches_whitelist, filter_whitelisted, matches_blacklist, filter_blacklisted
- Depends on: fnmatch, urllib.parse
- Used by: CLI layer

**URL Processing Layer:**
- Purpose: Canonicalize, deduplicate, and ID generation for URLs
- Location: `linkfeed/utils/url.py`
- Contains: canonicalize_url, generate_id (SHA256), is_valid_url, URLDeduplicator class
- Depends on: hashlib, urllib.parse
- Used by: CLI layer, parser layer

**Network Layer:**
- Purpose: Async HTTP fetching with session management
- Location: `linkfeed/utils/network.py`
- Contains: create_session, fetch_url (returns content, headers, redirects)
- Depends on: aiohttp
- Used by: CLI layer (process_url), parsers, scraper

**Tagging Layer:**
- Purpose: Optional LLM-based tag generation for content
- Location: `linkfeed/utils/tagging.py`
- Contains: generate_tags (async), parse_tags, create_openai_client
- Depends on: openai (AsyncOpenAI)
- Used by: CLI layer (process_url when --generate-tags enabled)

**Date Extraction Layer:**
- Purpose: Extract publication dates from HTML (with optional LLM fallback)
- Location: `linkfeed/utils/date_extraction.py`
- Contains: extract_date, extract_date_with_llm
- Depends on: beautifulsoup4, dateutil, openai
- Used by: Parser layer

## Data Flow

**Single-Feed Generation Flow:**

1. CLI loads config from linkfeed.yaml (or uses defaults)
2. URLs collected from: CLI args, config sources, markdown_dir, trello.file, website scrape
3. Whitelist/blacklist applied to filter URLs
4. Existing feed read (unless --rebuild flag)
5. URL deduplicator initialized with existing item IDs
6. Concurrent processing loop:
   - For each unique URL, get appropriate parser
   - Fetch content via network layer
   - Parse into FeedItem using specialized parser
   - Optional: Generate tags via OpenAI if --generate-tags enabled
7. Merge new items with existing feed (oldest items first, newest appended)
8. Write outputs: feed.json (JSON Feed format), feed.xml (RSS 2.0 format)
9. Optional: Generate index.html if --generate-site enabled

**Multi-Feed Generation Flow:**

1. CLI loads multi-config file with multiple feed definitions
2. For each named feed in config:
   - Collect URLs (same sources as single-feed)
   - Apply feed-level and global whitelist/blacklist
   - Process URLs concurrently
   - Write to output_dir/feed_name/feed.json and feed.xml
3. Generate index.html listing all feeds if --generate-site enabled

**Site Generation Flow:**

1. Scan feeds_dir recursively for all feed.json files
2. Load site.yaml for title/description defaults (fall back to CLI args)
3. For each feed.json:
   - Extract feed title, description, item count
   - Get last updated date from most recent item
   - Generate feed item HTML with links to JSON and RSS
   - Add RSS autodiscovery link
4. Render HTML template with all feeds
5. Write index.html to output_path

**State Management:**

- Configuration state: YAML files (linkfeed.yaml, site.yaml) and Pydantic models
- Feed state: Persisted in feed.json (JSON Feed format) between runs
- URL deduplication state: Tracked in memory via URLDeduplicator from existing feed IDs
- Session state: Async aiohttp ClientSession with persistent connection pooling
- OpenAI client state: Singleton AsyncOpenAI instance per run (if tags enabled)

## Key Abstractions

**BaseParser Registry:**
- Purpose: Extensible parser selection based on URL type
- Examples: `linkfeed/parsers/generic.py`, `linkfeed/parsers/youtube.py`, `linkfeed/parsers/media.py`
- Pattern: Register decorator pattern; get_parser() returns highest-priority parser that can_handle() the URL
- Fallback: GenericParser (priority 0) handles any URL as final fallback

**FeedItem Model:**
- Purpose: Unified representation of parsed content
- Examples: `linkfeed/models.py` FeedItem class with to_json_feed_item() method
- Pattern: Pydantic BaseModel with optional fields; supports Authors, Attachments, tags, dates
- Serialization: Converts to JSON Feed v1.1 item format, RSS enclosures and categories

**Feed Merging Logic:**
- Purpose: Preserve existing feed items while adding new ones
- Examples: `linkfeed/feed.py` merge_feeds function
- Pattern: Deduplicate by item.id; append new items after existing (ingestion order)
- Semantics: Oldest content first, newest content last

**Configuration Inheritance:**
- Purpose: Support single and multi-feed modes with shared global settings
- Examples: SingleFeedConfig vs NamedFeedConfig, global_blacklist/whitelist in MultiConfig
- Pattern: Per-feed settings override global settings; CLI args override all

## Entry Points

**CLI Command: `linkfeed run`:**
- Location: `linkfeed/cli.py` run() function
- Triggers: `linkfeed run` or `linkfeed run --config custom.yaml`
- Responsibilities: URL collection, filtering, deduplication, parsing, feed generation, optional site generation
- Returns: feed.json and feed.xml files

**CLI Command: `linkfeed generate-site`:**
- Location: `linkfeed/cli.py` generate_site_command() function
- Triggers: `linkfeed generate-site` or `linkfeed generate-site --feeds-dir ./feeds`
- Responsibilities: Scan feeds directory, load site configuration, generate index.html
- Returns: index.html with feed listing

**Async Helper: `process_url()`:**
- Location: `linkfeed/cli.py` process_url() function
- Triggers: Called by asyncio.gather in process_urls() loop
- Responsibilities: Single URL fetch → parse → optional tagging
- Returns: Optional FeedItem or None

**Multi-Feed Processor: `_run_multi_feed()`:**
- Location: `linkfeed/cli.py` _run_multi_feed() function
- Triggers: Called by run() when multi_config flag is True
- Responsibilities: Iterate feeds, process each with own output directory
- Returns: Multiple feed.json and feed.xml files

## Error Handling

**Strategy:** Graceful degradation with logging; continue processing on individual item failures

**Patterns:**

- **URL Fetching Failures:** Log warning, skip URL, continue with next
- **Parser Failures:** Log warning, return None, continue
- **Config Load Failures:** Click error message, sys.exit(1)
- **Feed I/O Failures:** Click error message, sys.exit(1)
- **API Failures (OpenAI):** Log warning, skip tagging, continue with untagged item
- **XML Sanitization:** Remove control characters, attempt RSS generation anyway
- **HTML Parsing:** Fallback from ReadabiliPy → basic HTML extraction → plain text

## Cross-Cutting Concerns

**Logging:** Python logging module with configurable levels (ERROR, INFO, DEBUG) via --verbose/--quiet flags. Logger instances created per module with __name__ pattern.

**Validation:**

- URL validation: is_valid_url() checks for http/https scheme and netloc
- Config validation: Pydantic models enforce required fields and type constraints
- Feed validation: FeedItem id and url are required; others optional with defaults
- Pattern validation: Whitelist/blacklist patterns matched via fnmatch and domain parsing

**Authentication:**

- OpenAI: Via OPENAI_API_KEY environment variable, AsyncOpenAI client handles auth
- No database authentication (feeds are stateless JSON files)
- No API key management beyond environment variables

**Concurrency:**

- asyncio.Semaphore(concurrency) limits concurrent URL fetches
- Default concurrency: 10 parallel requests
- aiohttp ClientSession connection pooling for HTTP reuse
- All URL processing is async with return_exceptions=True for fault tolerance

**Content Sanitization:**

- XML control character removal before RSS generation (regex-based)
- HTML escaping in site index template (&amp;, &lt;, &gt;, &quot;)
- URL canonicalization removes tracking parameters (utm_*, fbclid, gclid, etc.)

---

*Architecture analysis: 2026-01-25*
