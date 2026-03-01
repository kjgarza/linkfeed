# linkfeed justfile
# https://just.systems

# Default: list available recipes
default:
    @just --list

# ── Setup ────────────────────────────────────────────────────────────────────

# Create venv and install package (production deps)
install:
    uv venv
    uv pip install -e .

# Install with dev dependencies (pytest, coverage, etc.)
install-dev:
    uv venv
    uv pip install -e '.[dev]'

# ── Run ──────────────────────────────────────────────────────────────────────

# Generate feeds from config
run config="feed-config.yaml":
    uv run linkfeed run --config {{config}}

# Generate feeds from multi-feed config
run-multi config="claude-feed.yaml":
    uv run linkfeed run --config {{config}} --multi

# Generate feeds and regenerate site index
run-with-site config="claude-feed.yaml":
    uv run linkfeed run --config {{config}} --multi --generate-site

# Generate feeds with AI tags (requires OPENAI_API_KEY)
run-with-tags config="claude-feed.yaml":
    uv run linkfeed run --config {{config}} --multi --generate-site --generate-tags

# Rebuild feeds from scratch (discards existing feed.json)
rebuild config="feed-config.yaml":
    uv run linkfeed run --config {{config}} --rebuild

# Regenerate the site index only (no feed fetching)
generate-site feeds-dir="feeds":
    uv run linkfeed generate-site --feeds-dir {{feeds-dir}}

# ── Test ─────────────────────────────────────────────────────────────────────

# Run all tests
test:
    uv run pytest tests/

# Run a single test file
test-file file:
    uv run pytest {{file}}

# Run tests with coverage report
coverage:
    uv run pytest --cov=linkfeed tests/

# ── Lint & Format ────────────────────────────────────────────────────────────

# Check linting
lint:
    uv run ruff check .

# Auto-fix lint issues
lint-fix:
    uv run ruff check --fix .

# Format code
fmt:
    uv run ruff format .

# Check formatting without writing
fmt-check:
    uv run ruff format --check .

# Run lint + format check
check: lint fmt-check

# ── CI simulation ────────────────────────────────────────────────────────────

# Simulate the generate-feeds CI workflow locally
ci-feeds config="claude-feed.yaml":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -f "{{config}}" ]; then
        TAGS_FLAG=""
        if [ -n "${OPENAI_API_KEY:-}" ]; then
            TAGS_FLAG="--generate-tags"
        fi
        uv run linkfeed run --config {{config}} --multi --generate-site $TAGS_FLAG
    else
        echo "No {{config}} found, skipping feed generation"
    fi

# Simulate the generate-site CI workflow locally
ci-site feeds-dir="feeds":
    uv run linkfeed generate-site --feeds-dir {{feeds-dir}}
