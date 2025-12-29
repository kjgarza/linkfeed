"""CLI interface for linkfeed."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import aiohttp
import click
from openai import AsyncOpenAI

from linkfeed.config import (
    load_config,
    load_multi_config,
    is_multi_config,
    NamedFeedConfig,
)
from linkfeed.feed import (
    generate_rss,
    merge_feeds,
    read_existing_feed,
    write_json_feed,
)
from linkfeed.models import FeedItem
from linkfeed.parsers import get_parser
from linkfeed.site import generate_index_html
from linkfeed.utils.blacklist import filter_blacklisted
from linkfeed.utils.whitelist import filter_whitelisted
from linkfeed.utils.markdown import scan_markdown_directory
from linkfeed.utils.network import create_session, fetch_url
from linkfeed.utils.scraper import scrape_website_links
from linkfeed.utils.tagging import generate_tags, create_openai_client, DEFAULT_MODEL
from linkfeed.utils.trello import parse_trello_board
from linkfeed.utils.url import URLDeduplicator, is_valid_url

DEFAULT_CONCURRENCY = 10


@click.group()
def cli():
    """linkfeed - Generate JSON Feed and RSS from URLs."""
    pass


def setup_logging(verbose: bool, quiet: bool) -> None:
    """Configure logging based on verbosity."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


async def process_url(
    url: str,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    logger: logging.Logger,
    openai_client: Optional[AsyncOpenAI] = None,
    openai_model: str = DEFAULT_MODEL,
) -> Optional[FeedItem]:
    """Fetch and parse a single URL."""
    async with semaphore:
        logger.debug(f"Processing: {url}")

        parser = get_parser(url)
        if not parser:
            logger.warning(f"No parser for: {url}")
            return None

        result = await fetch_url(url, session=session)
        if not result:
            logger.warning(f"Failed to fetch: {url}")
            return None

        try:
            item = await parser.parse(
                result.url,
                result.content,
                result.content_type,
                result.content_length,
                session,
                openai_client,
            )
            if item:
                logger.debug(f"Parsed: {item.title or url}")

                # Generate tags if OpenAI client is provided
                if openai_client:
                    content = item.content_html or item.summary or ""
                    if content:
                        tags = await generate_tags(content, openai_client, openai_model)
                        # Append to existing tags
                        item.tags = list(set(item.tags + tags))
                        if tags:
                            logger.debug(f"Generated tags: {tags}")

                return item
        except Exception as e:
            logger.warning(f"Error parsing {url}: {e}")

        return None


async def process_urls(
    urls: list[str],
    concurrency: int,
    logger: logging.Logger,
    openai_client: Optional[AsyncOpenAI] = None,
    openai_model: str = DEFAULT_MODEL,
) -> list[FeedItem]:
    """Process multiple URLs concurrently."""
    semaphore = asyncio.Semaphore(concurrency)

    async with create_session() as session:
        tasks = [
            process_url(url, session, semaphore, logger, openai_client, openai_model)
            for url in urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    items = []
    for result in results:
        if isinstance(result, FeedItem):
            items.append(result)
        elif isinstance(result, Exception):
            logger.warning(f"Task failed: {result}")

    return items


@cli.command(name="generate-site")
@click.option(
    "--feeds-dir",
    "-f",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="feeds",
    help="Directory containing feeds (default: feeds)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output path for index.html (default: feeds/index.html)",
)
@click.option(
    "--title",
    "-t",
    type=str,
    help="Site title (overrides site.yaml)",
)
@click.option(
    "--description",
    type=str,
    help="Site description (overrides site.yaml)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Detailed logging",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Minimal output",
)
def generate_site_command(
    feeds_dir: Path,
    output: Optional[Path],
    title: Optional[str],
    description: Optional[str],
    verbose: bool,
    quiet: bool,
) -> None:
    """Generate static site index from feeds directory.
    
    Scans the feeds directory for all feed.json files and generates
    an index.html page listing all discovered feeds. Optionally reads
    site.yaml from feeds directory for default title/description.
    
    Examples:
        linkfeed generate-site
        linkfeed generate-site --feeds-dir ./my-feeds
        linkfeed generate-site --title "My Feeds" --description "Personal collection"
    """
    setup_logging(verbose, quiet)
    logger = logging.getLogger(__name__)
    
    # Determine output path
    if not output:
        output = feeds_dir / "index.html"
    
    logger.info(f"Generating site index from {feeds_dir}")
    
    try:
        generate_index_html(feeds_dir, output, title, description)
        click.echo(f"Generated site index at {output}")
    except Exception as e:
        click.echo(f"Error generating site: {e}", err=True)
        sys.exit(1)


@cli.command(name="run")
@click.argument("urls", nargs=-1)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=False, path_type=Path),
    default="linkfeed.yaml",
    help="Config file path (default: linkfeed.yaml)",
)
@click.option(
    "--from-markdown",
    "-m",
    "markdown_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Scan markdown directory for URLs",
)
@click.option(
    "--from-trello",
    "-t",
    "trello_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Parse Trello board JSON export for URLs",
)
@click.option(
    "--trello-list",
    "-L",
    "trello_lists",
    multiple=True,
    help="Filter Trello cards by list ID (repeatable)",
)
@click.option(
    "--website",
    "-W",
    "website_url",
    type=str,
    help="Scrape website for article links",
)
@click.option(
    "--json-out",
    "-j",
    type=click.Path(path_type=Path),
    default="feed.json",
    help="JSON Feed output path (default: feed.json)",
)
@click.option(
    "--rss-out",
    "-r",
    type=click.Path(path_type=Path),
    default="feed.xml",
    help="RSS output path (default: feed.xml)",
)
@click.option(
    "--output-dir",
    "-o",
    "output_dir",
    type=click.Path(path_type=Path),
    help="Output directory for feeds (creates feed.json and feed.xml inside)",
)
@click.option(
    "--multi",
    "-M",
    "multi_config",
    is_flag=True,
    help="Process multi-feed config file",
)
@click.option(
    "--generate-site",
    "-S",
    "generate_site",
    is_flag=True,
    help="Generate static index.html for all feeds",
)
@click.option(
    "--blacklist",
    "-b",
    "blacklist_patterns",
    multiple=True,
    help="Additional blacklist pattern (repeatable)",
)
@click.option(
    "--whitelist",
    "-w",
    "whitelist_patterns",
    multiple=True,
    help="Additional whitelist pattern (repeatable)",
)
@click.option(
    "--concurrency",
    "-C",
    type=int,
    default=DEFAULT_CONCURRENCY,
    help=f"Number of concurrent requests (default: {DEFAULT_CONCURRENCY})",
)
@click.option(
    "--generate-tags",
    "-g",
    is_flag=True,
    help="Generate tags using OpenAI (requires OPENAI_API_KEY)",
)
@click.option(
    "--openai-model",
    type=str,
    default=DEFAULT_MODEL,
    help=f"OpenAI model for tag generation (default: {DEFAULT_MODEL})",
)
@click.option(
    "--rebuild",
    "-R",
    is_flag=True,
    help="Rebuild feed from scratch (discard existing feed)",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Preview without writing files",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Detailed logging",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Minimal output",
)
def run(
    urls: tuple[str, ...],
    config_path: Path,
    markdown_dir: Optional[Path],
    trello_file: Optional[Path],
    trello_lists: tuple[str, ...],
    website_url: Optional[str],
    json_out: Path,
    rss_out: Path,
    output_dir: Optional[Path],
    multi_config: bool,
    generate_site: bool,
    blacklist_patterns: tuple[str, ...],
    whitelist_patterns: tuple[str, ...],
    concurrency: int,
    generate_tags: bool,
    openai_model: str,
    rebuild: bool,
    dry_run: bool,
    verbose: bool,
    quiet: bool,
) -> None:
    """Generate JSON Feed and RSS from URL links.

    URLs can be provided as arguments, from a config file, extracted
    from markdown files, scraped from websites, or parsed from Trello board exports.
    """
    setup_logging(verbose, quiet)
    logger = logging.getLogger(__name__)

    # Handle multi-feed config mode
    if multi_config:
        _run_multi_feed(
            config_path, output_dir or Path("feeds"), generate_site,
            concurrency, generate_tags, openai_model, rebuild, dry_run, logger,
            list(whitelist_patterns)
        )
        return

    # Initialize OpenAI client if tag generation is enabled
    openai_client = None
    if generate_tags:
        openai_client = create_openai_client()
        if not openai_client:
            click.echo("Error: Failed to create OpenAI client. Is OPENAI_API_KEY set?", err=True)
            sys.exit(1)
        logger.info(f"Tag generation enabled (model: {openai_model})")

    # Load config
    try:
        config = load_config(config_path)
    except ValueError as e:
        click.echo(f"Error loading config: {e}", err=True)
        sys.exit(1)

    # Collect all URLs
    all_urls: list[str] = []

    # From config
    all_urls.extend(config.sources)

    # From CLI arguments
    all_urls.extend(urls)

    # From markdown directory
    if markdown_dir:
        logger.info(f"Scanning markdown files in {markdown_dir}")
        all_urls.extend(scan_markdown_directory(markdown_dir))

    # From config markdown_dir setting
    if config.markdown_dir:
        md_path = Path(config.markdown_dir)
        if md_path.is_dir():
            logger.info(f"Scanning markdown from config: {config.markdown_dir}")
            all_urls.extend(scan_markdown_directory(md_path))

    # From Trello board JSON (CLI)
    if trello_file:
        list_filter = list(trello_lists) if trello_lists else None
        if list_filter:
            logger.info(f"Parsing Trello board {trello_file} (lists: {list_filter})")
        else:
            logger.info(f"Parsing Trello board {trello_file}")
        all_urls.extend(parse_trello_board(trello_file, list_ids=list_filter))

    # From config trello setting
    if config.trello and config.trello.file:
        trello_path = Path(config.trello.file)
        if trello_path.exists():
            list_filter = config.trello.lists if config.trello.lists else None
            logger.info(f"Parsing Trello from config: {config.trello.file}")
            all_urls.extend(parse_trello_board(trello_path, list_ids=list_filter))

    # From website scraping (CLI)
    if website_url:
        logger.info(f"Scraping website: {website_url}")
        scraped_urls = asyncio.run(_scrape_website(website_url))
        logger.info(f"Found {len(scraped_urls)} links from website")
        all_urls.extend(scraped_urls)

    # From config website setting
    if config.website:
        logger.info(f"Scraping website from config: {config.website}")
        scraped_urls = asyncio.run(_scrape_website(config.website))
        logger.info(f"Found {len(scraped_urls)} links from website")
        all_urls.extend(scraped_urls)

    if not all_urls:
        click.echo("No URLs to process", err=True)
        sys.exit(0)

    # Validate URLs
    valid_urls = [url for url in all_urls if is_valid_url(url)]
    if len(valid_urls) < len(all_urls):
        logger.warning(
            f"Skipped {len(all_urls) - len(valid_urls)} invalid URLs"
        )

    # Apply whitelist first
    whitelist = list(config.whitelist) + list(whitelist_patterns)
    whitelisted_urls = filter_whitelisted(valid_urls, whitelist)
    if len(whitelisted_urls) < len(valid_urls):
        logger.info(
            f"Filtered {len(valid_urls) - len(whitelisted_urls)} non-whitelisted URLs"
        )

    # Apply blacklist
    blacklist = list(config.blacklist) + list(blacklist_patterns)
    filtered_urls = filter_blacklisted(whitelisted_urls, blacklist)
    if len(filtered_urls) < len(whitelisted_urls):
        logger.info(
            f"Filtered {len(whitelisted_urls) - len(filtered_urls)} blacklisted URLs"
        )

    # Read existing feed for deduplication (unless rebuilding)
    existing_feed = None if rebuild else read_existing_feed(json_out)
    deduplicator = URLDeduplicator()

    if rebuild:
        logger.info("Rebuilding feed from scratch (existing feed discarded)")
    elif existing_feed:
        deduplicator.add_existing_ids([item.id for item in existing_feed.items])
        logger.info(f"Loaded {len(existing_feed.items)} existing items")

    # Deduplicate URLs
    unique_urls = []
    for url in filtered_urls:
        if not deduplicator.is_duplicate(url):
            deduplicator.mark_seen(url)
            unique_urls.append(url)

    if not unique_urls:
        if rebuild:
            click.echo("No URLs to process for rebuild")
        else:
            click.echo("No new URLs to process")
        sys.exit(0)

    logger.info(f"Processing {len(unique_urls)} URLs (concurrency: {concurrency})")

    # Process URLs concurrently
    new_items = asyncio.run(
        process_urls(unique_urls, concurrency, logger, openai_client, openai_model)
    )

    if not new_items:
        click.echo("No items successfully parsed")
        sys.exit(0)

    # Merge with existing feed
    feed_meta = {
        "title": config.feed.title,
        "home_page_url": config.feed.home_page_url,
        "feed_url": config.feed.feed_url,
        "description": config.feed.description,
        "language": config.feed.language,
    }

    merged_feed = merge_feeds(existing_feed, new_items, feed_meta)

    # Determine output paths
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_out = output_dir / "feed.json"
        rss_out = output_dir / "feed.xml"

    # Output
    if dry_run:
        if rebuild:
            click.echo(f"Would rebuild feed with {len(new_items)} items")
        else:
            click.echo(f"Would add {len(new_items)} new items to feed")
        for item in new_items:
            click.echo(f"  - {item.title or item.url}")
    else:
        try:
            write_json_feed(merged_feed, json_out)
            logger.info(f"Wrote JSON Feed to {json_out}")

            generate_rss(merged_feed, rss_out)
            logger.info(f"Wrote RSS to {rss_out}")

            if rebuild:
                click.echo(f"Rebuilt feed with {len(merged_feed.items)} items")
            else:
                click.echo(
                    f"Added {len(new_items)} items (total: {len(merged_feed.items)})"
                )
        except IOError as e:
            click.echo(f"Error writing output: {e}", err=True)
            sys.exit(1)


async def _scrape_website(url: str) -> list[str]:
    """Scrape a website for article links."""
    async with create_session() as session:
        return await scrape_website_links(url, session)


def _run_multi_feed(
    config_path: Path,
    output_dir: Path,
    generate_site: bool,
    concurrency: int,
    do_generate_tags: bool,
    openai_model: str,
    rebuild: bool,
    dry_run: bool,
    logger: logging.Logger,
    cli_whitelist: list[str] = None,
) -> None:
    """Process multiple feeds from a multi-feed config."""
    try:
        multi = load_multi_config(config_path)
    except ValueError as e:
        click.echo(f"Error loading multi-feed config: {e}", err=True)
        sys.exit(1)

    if not multi.feeds:
        click.echo("No feeds defined in config", err=True)
        sys.exit(1)

    # Initialize OpenAI client if needed
    openai_client = None
    if do_generate_tags:
        openai_client = create_openai_client()
        if not openai_client:
            click.echo("Error: Failed to create OpenAI client", err=True)
            sys.exit(1)

    logger.info(f"Processing {len(multi.feeds)} feeds")

    for feed_config in multi.feeds:
        logger.info(f"Processing feed: {feed_config.name}")

        # Determine output directory for this feed
        feed_output_dir = output_dir / (feed_config.output_dir or feed_config.name)

        # Collect URLs
        all_urls: list[str] = list(feed_config.sources)

        # From markdown_dir if configured
        if feed_config.markdown_dir:
            md_path = Path(feed_config.markdown_dir)
            if md_path.is_dir():
                logger.info(f"  Scanning markdown: {feed_config.markdown_dir}")
                all_urls.extend(scan_markdown_directory(md_path))

        # From trello if configured
        if feed_config.trello and feed_config.trello.file:
            trello_path = Path(feed_config.trello.file)
            if trello_path.exists():
                list_filter = feed_config.trello.lists if feed_config.trello.lists else None
                logger.info(f"  Parsing Trello: {feed_config.trello.file}")
                all_urls.extend(parse_trello_board(trello_path, list_ids=list_filter))

        # Scrape website if configured
        if feed_config.website:
            logger.info(f"  Scraping: {feed_config.website}")
            scraped = asyncio.run(_scrape_website(feed_config.website))
            logger.info(f"  Found {len(scraped)} links")
            all_urls.extend(scraped)

        if not all_urls:
            logger.warning(f"  No URLs for feed {feed_config.name}")
            continue

        # Apply whitelists (feed-level, global, and CLI)
        whitelist = list(feed_config.whitelist) + list(multi.global_whitelist)
        if cli_whitelist:
            whitelist.extend(cli_whitelist)
        whitelisted_urls = filter_whitelisted(all_urls, whitelist)

        # Apply blacklists
        blacklist = list(feed_config.blacklist) + list(multi.global_blacklist)
        filtered_urls = filter_blacklisted(whitelisted_urls, blacklist)
        valid_urls = [u for u in filtered_urls if is_valid_url(u)]

        # Read existing feed (unless rebuilding)
        json_out = feed_output_dir / "feed.json"
        rss_out = feed_output_dir / "feed.xml"
        existing_feed = None if rebuild else read_existing_feed(json_out)

        deduplicator = URLDeduplicator()
        if rebuild:
            logger.info(f"  Rebuilding {feed_config.name} from scratch")
        elif existing_feed:
            deduplicator.add_existing_ids([item.id for item in existing_feed.items])

        unique_urls = []
        for url in valid_urls:
            if not deduplicator.is_duplicate(url):
                deduplicator.mark_seen(url)
                unique_urls.append(url)

        if not unique_urls:
            if rebuild:
                logger.info(f"  No URLs to process for {feed_config.name}")
            else:
                logger.info(f"  No new URLs for {feed_config.name}")
            continue

        logger.info(f"  Processing {len(unique_urls)} URLs")

        # Process URLs
        new_items = asyncio.run(
            process_urls(unique_urls, concurrency, logger, openai_client, openai_model)
        )

        if not new_items:
            logger.warning(f"  No items parsed for {feed_config.name}")
            continue

        # Merge and write
        feed_meta = {
            "title": feed_config.feed.title,
            "home_page_url": feed_config.feed.home_page_url,
            "feed_url": feed_config.feed.feed_url,
            "description": feed_config.feed.description,
            "language": feed_config.feed.language,
        }

        merged_feed = merge_feeds(existing_feed, new_items, feed_meta)

        if not dry_run:
            feed_output_dir.mkdir(parents=True, exist_ok=True)
            write_json_feed(merged_feed, json_out)
            generate_rss(merged_feed, rss_out)
            if rebuild:
                logger.info(f"  Rebuilt {feed_config.name} with {len(merged_feed.items)} items")
            else:
                logger.info(f"  Wrote {len(new_items)} new items to {feed_output_dir}")
        else:
            if rebuild:
                click.echo(f"  Would rebuild {feed_config.name} with {len(new_items)} items")
            else:
                click.echo(f"  Would add {len(new_items)} items to {feed_config.name}")

    # Generate static site index
    if generate_site and not dry_run:
        index_path = output_dir / "index.html"
        generate_index_html(output_dir, index_path)
        click.echo(f"Generated site index at {index_path}")


if __name__ == "__main__":
    cli()
