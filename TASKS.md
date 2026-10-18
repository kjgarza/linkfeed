

- [x] confirm the cli should be checking the feed before running again from the feeds/ folder.
- [x] have a whitelist for links similar to the blacklist but the opposite
- [x] modify the cron job to once a week
- [x] Site generation should be for all feeds in feeds/ folder. maybe use nunjucks for templating
- [x] Add --rebuild flag to discard existing feed and rebuild from scratch

## Implementation Summary

### 1. Feed Checking (Already Implemented)
The CLI already checks existing feeds before running:
- `read_existing_feed()` loads existing feed.json files
- Deduplication prevents re-processing URLs
- Works for both single and multi-feed modes

### 2. Whitelist Feature ✅ 
Added comprehensive whitelist functionality:
- Created `linkfeed/utils/whitelist.py` with pattern matching
- Added `whitelist` field to SingleFeedConfig and NamedFeedConfig
- Added `global_whitelist` field to MultiConfig
- Added `--whitelist` / `-w` CLI flag (changed website from -w to -W)
- Whitelist applied before blacklist (allow then deny pattern)
- Supports glob patterns: `*.domain.com`, exact domains, full URLs
- Tests in `tests/test_whitelist.py`

### 3. Cron Schedule ✅
Updated `.github/workflows/generate-feeds.yml`:
- Changed from daily (`0 0 * * *`) to weekly (`0 0 * * 0`)
- Runs every Sunday at midnight UTC

### 4. Site Generation ✅ (Already Working)
The site generation already works for all feeds:
- `generate_index_html()` uses `rglob("feed.json")` to find all feeds
- Recursively scans the entire feeds/ directory
- Generates index.html with links to all feeds
- No templating engine needed - uses embedded HTML template

### 5. Rebuild Feature ✅
Added `--rebuild` / `-R` flag to rebuild feeds from scratch:
- Discards existing feed and processes all URLs
- Useful for refreshing all metadata or testing new configurations
- Works in both single and multi-feed modes
- Respects `--dry-run` for safe preview
- Tests in `tests/test_rebuild.py`
- Documented in README with examples
