# Codebase Concerns

**Analysis Date:** 2026-01-25

## Tech Debt

**Large CLI File - Monolithic Command Handler:**
- Issue: `linkfeed/cli.py` contains 708 lines with multiple command handlers, nested async functions, and significant business logic mixing. The `run()` command at line 342 is particularly large (200+ lines) with deep nesting for URL collection from multiple sources.
- Files: `linkfeed/cli.py` (342-705 lines for single command)
- Impact: Difficult to test individual features, high cyclomatic complexity, maintenance burden when adding new URL sources or feed handling logic
- Fix approach: Extract URL collection logic into separate module (`url_collection.py`), create command handler classes or helper functions, break `_run_multi_feed()` into smaller functions

**Redundant Paragraph Extraction Logic:**
- Issue: `linkfeed/parsers/generic.py` has two nearly identical methods `_extract_best_paragraph()` and `_extract_first_paragraph()` with same selection criteria (checking 4 paragraphs, filtering by 100+ char minimum, taking longest). This violates DRY principle.
- Files: `linkfeed/parsers/generic.py` (203-259 lines)
- Impact: Bug fixes or refinements must be applied in two places; increases test burden
- Fix approach: Create single parameterized method `_extract_best_paragraph_from_source()` that accepts content source (list vs BeautifulSoup)

**Bare Except Clause Swallowing Errors:**
- Issue: `linkfeed/utils/url.py` lines 55-56 and 72, `linkfeed/utils/scraper.py` lines 121-122, and similar broad exception handling in multiple locations use bare `except Exception:` which masks unexpected errors
- Files: `linkfeed/utils/url.py`, `linkfeed/utils/scraper.py`, `linkfeed/utils/network.py`
- Impact: When unexpected errors occur, they're silently converted to fallback values (None, empty list) with only debug logging. Makes production debugging difficult.
- Fix approach: Log the full exception with traceback, be more specific about exception types caught

**OpenAI Client Creation Side Effect:**
- Issue: `create_openai_client()` in `linkfeed/utils/tagging.py` line 113 is called during CLI initialization without guarantees about when the API key is available. The CLI creates the client at line 384 after config loading, but this is still implicit behavior.
- Files: `linkfeed/cli.py` (384), `linkfeed/utils/tagging.py` (113-119)
- Impact: API key missing errors appear late in execution; harder to validate configuration early
- Fix approach: Create explicit validation function that checks for API key before parsing content; return error immediately

**Inconsistent Session Management:**
- Issue: Multiple places manually create aiohttp sessions and manage close() calls (`linkfeed/utils/scraper.py` 57-82, `linkfeed/utils/network.py` 34-76). `create_session()` helper exists at `linkfeed/utils/network.py` 118-124 but not consistently used. Potential resource leaks if exceptions occur before finally blocks.
- Files: `linkfeed/utils/scraper.py`, `linkfeed/utils/network.py`, `linkfeed/cli.py` (438, 445)
- Impact: Session cleanup may not occur if unhandled exceptions interrupt finally block
- Fix approach: Use context manager for all session creation, enforce use of `create_session()` context manager pattern

## Known Bugs

**Date Fallback to Current Time:**
- Symptom: Articles without publication dates get current timestamp, which:
  1. Can cause stale articles to appear new in RSS (sorted by date)
  2. Makes it impossible to distinguish "date was not found" from "parsed today"
- Files: `linkfeed/parsers/generic.py` (127-128), behavior triggered when `date_published` is None
- Trigger: Any page without metadata date, OpenGraph date, Schema.org date, or extractable byline date
- Workaround: Manually add dates to feed.json after generation, or filter/sort manually
- Fix approach: Use article URL or hash as secondary sort key; add optional `date_not_found` flag to FeedItem

**Sitemap XML Parsing Doesn't Follow Recursive Links:**
- Symptom: When a website has `sitemap-index.xml` pointing to other sitemaps, only the index is parsed and logged but not recursively fetched
- Files: `linkfeed/utils/scraper.py` (105-110)
- Trigger: Websites with sitemap indices (common for large sites)
- Workaround: Directly target specific sitemap URLs if known
- Fix approach: Implement recursive sitemap fetching with depth limit

**HTML Decoding Silently Replaces Invalid UTF-8:**
- Symptom: Non-UTF8 HTML pages have invalid bytes silently replaced with replacement character (U+FFFD), potentially corrupting content
- Files: `linkfeed/parsers/generic.py` (45)
- Trigger: Pages not properly UTF-8 encoded
- Workaround: Content is still usable but may have garbled text
- Fix approach: Log warning when replacement occurs, track encoding from HTTP headers

## Security Considerations

**No Validation on Config URLs:**
- Risk: User-supplied URLs in config files are not validated before being added to feed sources. Malformed or extremely long URLs could cause issues.
- Files: `linkfeed/config.py` (88-96), `linkfeed/cli.py` (400-426)
- Current mitigation: URLs are filtered through `is_valid_url()` at line 454 in cli.py, checked at `linkfeed/utils/url.py` (67-73)
- Recommendations: Add URL length limits in config validation; add hostname whitelist/blacklist at config level

**No Rate Limiting on Web Scraping:**
- Risk: `scrape_website_links()` in `linkfeed/utils/scraper.py` has no rate limiting. Could scrape same domain excessively if configured with high concurrency.
- Files: `linkfeed/utils/scraper.py`, `linkfeed/cli.py` (300-305)
- Current mitigation: TCP connection limits at 10/host (line 122 in network.py)
- Recommendations: Add per-domain request throttling, respect robots.txt, add configurable delay between requests

**Open Graph/Meta Tag XSS in HTML Output:**
- Risk: `linkfeed/site.py` does call `_escape_html()` but this is basic character escaping. Malicious open-graph descriptions could still bypass naive escaping.
- Files: `linkfeed/site.py` (263-270), (171-178)
- Current mitigation: Uses HTML entities escaping which handles basic cases
- Recommendations: Use HTML sanitization library (bleach) instead of character replacement; validate feed data on read

**No Timeout on Content Downloads:**
- Risk: `linkfeed/utils/network.py` sets timeout to 10 seconds per request, but with 100+ URLs and default concurrency of 10, total runtime could be 100+ seconds. No overall timeout.
- Files: `linkfeed/utils/network.py` (31, 40)
- Current mitigation: Individual request timeout exists
- Recommendations: Add overall operation timeout, add configurable timeout per source type

**Missing Authentication for Trello:**
- Risk: `linkfeed/utils/trello.py` parses local JSON exports only (no API access), but no validation of export file integrity
- Files: `linkfeed/utils/trello.py`
- Current mitigation: Local file parsing only
- Recommendations: Add file hash validation, warn if JSON structure is unexpected

## Performance Bottlenecks

**Synchronous ReadabiliPy Blocking Async Event Loop:**
- Problem: `linkfeed/parsers/generic.py` line 65 calls `simple_json_from_html_string()` which is synchronous blocking I/O in async context
- Files: `linkfeed/parsers/generic.py` (65), (48)
- Cause: ReadabiliPy doesn't expose async API; blocking call in async parse() method
- Impact: During concurrent URL processing (semaphore at line 120 in cli.py), this blocks the event loop for 100-500ms per page
- Improvement path: Use `asyncio.to_thread()` to run ReadabiliPy in executor, or switch to `trafilatura` which supports async

**BeautifulSoup Fallback Creates Second Soup Object:**
- Problem: `linkfeed/parsers/generic.py` creates BeautifulSoup objects twice: once inside ReadabiliPy result (line 102), and again on line 143. If ReadabiliPy fails, HTML is re-parsed.
- Files: `linkfeed/parsers/generic.py` (102, 143)
- Impact: 15-20% slower fallback path
- Improvement path: Parse once on entry, pass parsed soup to multiple extraction methods

**Feed Merge Creates Large List on Every Run:**
- Problem: `linkfeed/feed.py` line 56 creates `all_items = existing.items + unique_new` as list concatenation. With large feeds (1000+ items), this allocates large temporary list.
- Files: `linkfeed/feed.py` (49-67)
- Impact: Memory spike with large feeds, O(n) copy operation
- Improvement path: Use list comprehension or iterator chaining, or implement linked-list like structure

**No Feed Pagination or Streaming:**
- Problem: Entire feed is loaded into memory and JSON dumped at once. No streaming or pagination support.
- Files: `linkfeed/feed.py` (40-46), `linkfeed/models.py` (83-103)
- Impact: 100K+ item feeds could consume significant memory
- Improvement path: Add streaming JSON generation, implement cursor-based pagination

## Fragile Areas

**Generic Parser Relies on Heuristics:**
- Files: `linkfeed/parsers/generic.py`
- Why fragile: Uses fallback chain (ReadabiliPy → BeautifulSoup) with many heuristics (4-paragraph limit, 100-char minimum, longest paragraph). Different sites format content differently.
- Safe modification: Add integration tests for top 20 popular domains; test date extraction on samples; add logging for which extraction path succeeded
- Test coverage: 110 lines of tests in `test_parsers.py` but only basic cases; no tests for real pages

**Concurrent Request Semaphore Not Adaptive:**
- Files: `linkfeed/cli.py` (120), default concurrency 10
- Why fragile: Hard-coded 10 concurrency fails if host has strict rate limits or if network is slow. No adaptive backoff.
- Safe modification: Make semaphore configurable, add exponential backoff on 429/503
- Test coverage: No load testing; no rate-limit handling tests

**URL Deduplication by Hash Vulnerable to Collision:**
- Files: `linkfeed/utils/url.py` (85-105)
- Why fragile: Uses first 16 chars of SHA256 (2^64 collision space). With 1M items, birthday paradox gives ~0.003% collision probability, but hash collisions are not detected.
- Safe modification: Use full hash or UUID, add collision detection logging
- Test coverage: No tests for collision scenarios

**YAML Config Parsing Silently Defaults:**
- Files: `linkfeed/config.py` (64-96)
- Why fragile: Missing config returns empty `SingleFeedConfig()` with all defaults. No warning if file is unreadable or malformed until parsing fails.
- Safe modification: Log warnings for missing required fields, validate after loading
- Test coverage: No tests for malformed YAML; no tests for missing config file

## Scaling Limits

**In-Memory Feed Storage:**
- Current capacity: ~50K items before significant memory overhead (assuming ~500 bytes per item)
- Limit: At 100K items, feed.json file size reaches ~50MB, feed object takes ~50MB RAM
- Scaling path:
  1. Implement database backend (SQLite minimum, PostgreSQL for production)
  2. Add pagination/streaming output
  3. Implement archival strategy (move old items to separate feeds)

**Concurrent Requests Limited by Connection Pool:**
- Current capacity: 100 total connections, 10 per host (line 122 in network.py)
- Limit: With 50+ hosts, effective concurrency drops significantly
- Scaling path: Make pool size configurable, add per-domain queuing, implement adaptive backoff

**No Feed Versioning/Rollback:**
- Current capacity: One version only; accidental corruption or invalid parsing loses all history
- Limit: Cannot recover from bad run without manual intervention
- Scaling path: Keep timestamped backups, add rollback command, implement transaction-like updates

## Dependencies at Risk

**ReadabiliPy Abandoned in Production Use:**
- Risk: Library has been dormant; no response to issues. Readability algorithm has known bugs with modern websites.
- Impact: Content extraction degrades over time as web formats change
- Migration plan: Switch to `trafilatura` (actively maintained, faster, better accuracy) or `newspaper3k`

**OpenAI Dependency for Tag Generation:**
- Risk: Adds dependency on external service; OpenAI API changes could break feature; costs money
- Impact: Tag generation fails silently if API is unavailable; no fallback
- Migration plan: Make tag generation fully optional, add local ML fallback (e.g., TF-IDF), add caching to reduce API calls

**Dateutil Library for Date Parsing:**
- Risk: Library has known performance issues with ambiguous dates; uses external lexicon
- Impact: Date extraction slow for complex dates; poor accuracy for non-English dates
- Migration plan: Use Python 3.13's zoneinfo (built-in), create domain-specific date parsing rules

## Missing Critical Features

**No Duplicate Content Detection:**
- Problem: If same article is crawled from multiple sources, it creates duplicate feed items (only URL deduplication)
- Blocks: Cannot have multi-source feeds without verbose duplication
- Priority: High - affects multi-feed quality significantly

**No Feed Caching/Conditional Requests:**
- Problem: Every `run` fetches full HTML even for unchanged URLs. No ETags, Last-Modified headers checked.
- Blocks: Cannot efficiently run frequent updates; wastes bandwidth
- Priority: Medium - impacts scaling

**No Subscription/OPML Support:**
- Problem: Feed index is HTML only, not machine-readable. Cannot export feed list.
- Blocks: Cannot backup or share feed configuration
- Priority: Low - nice-to-have

**No Async Markdown Directory Scanning:**
- Problem: `linkfeed/utils/markdown.py` reads file synchronously in async context
- Blocks: Performance degrades with large markdown directories
- Priority: Medium

## Test Coverage Gaps

**Parser Extraction Untested with Real Pages:**
- What's not tested: Generic parser's fallback chain (ReadabiliPy → BeautifulSoup) only tested on synthetic HTML snippets
- Files: `linkfeed/tests/test_parsers.py` (110 lines)
- Risk: Regression when web pages change format; extraction logic brittle
- Priority: High - parser is critical path

**No Tests for LLM-Based Date/Tag Extraction:**
- What's not tested: `extract_date_with_llm()` and `generate_tags()` never run in tests. No mock OpenAI responses.
- Files: `linkfeed/utils/date_extraction.py`, `linkfeed/utils/tagging.py`
- Risk: Feature silently fails if LLM returns unexpected format; no verification of prompt correctness
- Priority: High - feature is opt-in but should not break silently

**No Error Path Tests:**
- What's not tested: Network failures, malformed feeds, corrupted JSON, bad config
- Files: Most modules have exception handlers but no test coverage
- Risk: Error messages may be unclear; graceful degradation untested
- Priority: Medium

**No Integration Tests for Multi-Feed:**
- What's not tested: `_run_multi_feed()` logic with multiple feeds, deduplication across feeds
- Files: `linkfeed/tests/test_rebuild.py` covers single-feed rebuild only
- Risk: Multi-feed mode has edge cases around global blacklist/whitelist application
- Priority: Medium

**No Website Scraping Tests:**
- What's not tested: `scrape_website_links()` behavior, sitemap parsing, link filtering
- Files: `linkfeed/tests/test_utils.py` has basic utils tests but no scraper tests
- Risk: Scraper is fragile (CSS selectors, domain matching); no regression detection
- Priority: Medium - scraper is feature, not core

---

*Concerns audit: 2026-01-25*
