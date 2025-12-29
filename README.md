# linkfeed

Generate JSON Feed and RSS from URL links. Supports multiple input sources including URLs, markdown files, Trello boards, and website scraping.

## Installation

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Quick Start

```bash
# Process URLs directly
linkfeed run https://example.com/article1 https://example.com/article2

# Rebuild feed from scratch (discard existing items)
linkfeed run --rebuild --config linkfeed.yaml

# Scrape a website for article links
linkfeed run --website https://news.example.com

# Extract URLs from markdown files
linkfeed run --from-markdown ./notes/

# Parse URLs from Trello board export
linkfeed run --from-trello board.json

# Use a config file
linkfeed run --config linkfeed.yaml

# Generate with AI-powered tags (requires OPENAI_API_KEY)
linkfeed run --generate-tags https://example.com/article

# Dry run (preview without writing)
linkfeed run --dry-run https://example.com/article

# Generate static site index (standalone)
linkfeed generate-site

# Generate site with custom title/description
linkfeed generate-site --title "My Feeds" --description "Personal collection"

# Generate site from custom directory
linkfeed generate-site --feeds-dir ./my-feeds --output ./my-feeds/index.html
```

## Configuration

### Basic Config (`linkfeed.yaml`)

```yaml
feed:
  title: "My Link Feed"
  home_page_url: "https://example.com"
  feed_url: "https://example.com/feed.json"
  description: "Links I find interesting"
  language: "en"

sources:
  - https://example.com/article1
  - https://example.com/article2

# Optional: Only allow URLs from these domains
whitelist:
  - "example.com"
  - "*.trusted.com"

# Optional: Block specific patterns (applied after whitelist)
blacklist:
  - "*.tracking.com"
  - "ads.example.com"
```

### Config with Markdown Source

```yaml
feed:
  title: "Notes Feed"
  description: "Links extracted from my notes"

# URLs are extracted from all .md files in the directory
markdown_dir: "./notes"

# Can combine with static sources
sources:
  - https://example.com/pinned-article

blacklist:
  - "*.internal.com"
```

### Config with Trello Board

```yaml
feed:
  title: "Reading List"
  description: "Articles from my Trello reading board"

# Export your Trello board as JSON
trello:
  file: "./board.json"
  lists:  # Optional: filter by list IDs
    - "64f46d5d347f9e0a1ba4432b"
    - "62f8c2061ae2077a4159c046"

blacklist:
  - "trello.com"
```

### Config with Website Scraping

```yaml
feed:
  title: "Tech News"
  description: "Latest articles from tech sites"

# Automatically scrape links from a website
website: "https://news.ycombinator.com"

blacklist:
  - "*.reddit.com"
  - "twitter.com"
```

### Multi-Feed Config (`feeds.yaml`)

For managing multiple feeds, use the multi-feed format with `--multi` flag:

```yaml
# Use with: linkfeed --config feeds.yaml --multi --generate-site

global_blacklist:
  - "*.tracking.com"

global_whitelist:
  - "*.github.com"
  - "example.com"

feeds:
  - name: tech
    feed:
      title: "Tech News"
      description: "Technology articles"
    website: "https://news.ycombinator.com"
    whitelist:
      - "*.ycombinator.com"
      - "github.com"
    blacklist:
      - "*.reddit.com"

  - name: reading-list
    feed:
      title: "Reading List"
      description: "Articles from Trello"
    trello:
      file: "./trello-export.json"
      lists:
        - "64f46d5d347f9e0a1ba4432b"

  - name: notes
    feed:
      title: "From Notes"
      description: "Links from markdown notes"
    markdown_dir: "./notes"

  - name: combined
    feed:
      title: "Combined Feed"
      description: "Multiple sources in one feed"
    sources:
      - "https://example.com/pinned"
    markdown_dir: "./bookmarks"
    website: "https://blog.example.com"
```

### Site Index Configuration

Optionally create a `site.yaml` file in your feeds directory to customize the index page:

```yaml
# feeds/site.yaml
title: "My Feed Collection"
description: "A curated collection of RSS and JSON feeds"
```

If not present, defaults to "Feed Index" and generic description.

## Commands

### `linkfeed run`

Generate feeds from URLs and various sources.

| Option | Description |
|--------|-------------|
| `-c, --config PATH` | Config file path (default: linkfeed.yaml) |
| `-m, --from-markdown DIR` | Extract URLs from markdown files |
| `-t, --from-trello FILE` | Parse Trello board JSON export |
| `-L, --trello-list ID` | Filter Trello cards by list ID (repeatable) |
| `-W, --website URL` | Scrape website for article links |
| `-o, --output-dir PATH` | Output directory for feeds |
| `-j, --json-out PATH` | JSON Feed output path (default: feed.json) |
| `-r, --rss-out PATH` | RSS output path (default: feed.xml) |
| `-M, --multi` | Process multi-feed config file |
| `-S, --generate-site` | Generate static index.html for all feeds |
| `-b, --blacklist PATTERN` | Blacklist pattern (repeatable) |
| `-w, --whitelist PATTERN` | Whitelist pattern (repeatable) |
| `-C, --concurrency N` | Concurrent requests (default: 10) |
| `-g, --generate-tags` | Generate tags using OpenAI |
| `--openai-model MODEL` | OpenAI model (default: gpt-4o-mini) |
| `-R, --rebuild` | Rebuild feed from scratch (discard existing) |
| `-n, --dry-run` | Preview without writing files |
| `-v, --verbose` | Detailed logging |
| `-q, --quiet` | Minimal output |

### `linkfeed generate-site`

Generate static site index from feeds directory (no feed generation).

| Option | Description |
|--------|-------------|
| `-f, --feeds-dir PATH` | Directory containing feeds (default: feeds) |
| `-o, --output PATH` | Output path for index.html (default: feeds/index.html) |
| `-t, --title TEXT` | Site title (overrides site.yaml) |
| `--description TEXT` | Site description (overrides site.yaml) |
| `-v, --verbose` | Detailed logging |
| `-q, --quiet` | Minimal output |

**Use Cases:**
- Regenerate site index after manual feed edits
- Update site styling without re-fetching feeds
- Deploy static site independently

**Examples:**
```bash
# Generate with defaults (reads feeds/site.yaml if present)
linkfeed generate-site

# Override title and description
linkfeed generate-site --title "Tech Feeds" --description "My tech articles"

# Custom feeds directory
linkfeed generate-site --feeds-dir ./my-feeds
```

## Feed Management

### Incremental Updates (Default)

By default, linkfeed appends new items to existing feeds without re-processing URLs that already exist. This is efficient for regular updates.

```bash
# First run - creates feed with 10 items
linkfeed --config linkfeed.yaml

# Second run - only adds new items
linkfeed --config linkfeed.yaml
```

### Rebuild from Scratch

Use the `--rebuild` flag to discard the existing feed and rebuild it completely from all sources. This is useful when:
- You've modified parser logic and want to re-parse existing URLs
- You want to refresh metadata for all items
- You're testing new configurations

```bash
# Rebuild entire feed from scratch
linkfeed --rebuild --config linkfeed.yaml

# Rebuild all feeds in multi-feed mode
linkfeed --rebuild --config feeds.yaml --multi
```

**Note:** The `--rebuild` flag processes all URLs from your sources, ignoring any existing feed data.

## Output

- `feed.json`: JSON Feed v1.1 format
- `feed.xml`: RSS 2.0 format
- `index.html`: Static site index (with `--generate-site`)

## GitHub Actions

For automated feed generation, see `.github/workflows/generate-feeds.yml`. It supports:
- Weekly scheduled runs (Sundays at midnight UTC)
- GitHub Pages deployment
- Optional OpenAI tag generation (set `OPENAI_API_KEY` secret)

## License

MIT
