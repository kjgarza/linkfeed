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
linkfeed https://example.com/article1 https://example.com/article2

# Scrape a website for article links
linkfeed --website https://news.example.com

# Extract URLs from markdown files
linkfeed --from-markdown ./notes/

# Parse URLs from Trello board export
linkfeed --from-trello board.json

# Use a config file
linkfeed --config linkfeed.yaml

# Generate with AI-powered tags (requires OPENAI_API_KEY)
linkfeed --generate-tags https://example.com/article

# Dry run (preview without writing)
linkfeed --dry-run https://example.com/article
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

feeds:
  - name: tech
    feed:
      title: "Tech News"
      description: "Technology articles"
    website: "https://news.ycombinator.com"
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

## CLI Options

| Option | Description |
|--------|-------------|
| `-c, --config PATH` | Config file path (default: linkfeed.yaml) |
| `-m, --from-markdown DIR` | Extract URLs from markdown files |
| `-t, --from-trello FILE` | Parse Trello board JSON export |
| `-L, --trello-list ID` | Filter Trello cards by list ID (repeatable) |
| `-w, --website URL` | Scrape website for article links |
| `-o, --output-dir PATH` | Output directory for feeds |
| `-j, --json-out PATH` | JSON Feed output path (default: feed.json) |
| `-r, --rss-out PATH` | RSS output path (default: feed.xml) |
| `-M, --multi` | Process multi-feed config file |
| `-S, --generate-site` | Generate static index.html for all feeds |
| `-b, --blacklist PATTERN` | Blacklist pattern (repeatable) |
| `-C, --concurrency N` | Concurrent requests (default: 10) |
| `-g, --generate-tags` | Generate tags using OpenAI |
| `--openai-model MODEL` | OpenAI model (default: gpt-4o-mini) |
| `-n, --dry-run` | Preview without writing files |
| `-v, --verbose` | Detailed logging |
| `-q, --quiet` | Minimal output |

## Output

- `feed.json`: JSON Feed v1.1 format
- `feed.xml`: RSS 2.0 format
- `index.html`: Static site index (with `--generate-site`)

## GitHub Actions

For automated feed generation, see `.github/workflows/generate-feeds.yml`. It supports:
- Daily scheduled runs
- GitHub Pages deployment
- Optional OpenAI tag generation (set `OPENAI_API_KEY` secret)

## License

MIT
