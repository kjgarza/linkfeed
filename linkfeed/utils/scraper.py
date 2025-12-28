"""Website scraper for discovering article links."""

import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from linkfeed.utils.url import is_valid_url

logger = logging.getLogger(__name__)

# Common article link selectors
ARTICLE_SELECTORS = [
    "article a[href]",
    "main a[href]",
    ".post a[href]",
    ".entry a[href]",
    ".article a[href]",
    ".content a[href]",
    "a[href*='/post/']",
    "a[href*='/article/']",
    "a[href*='/blog/']",
    "a[href*='/news/']",
]

# Patterns to exclude (navigation, assets, etc.)
EXCLUDE_PATTERNS = [
    r"^#",
    r"^javascript:",
    r"^mailto:",
    r"\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$",
    r"/(tag|category|author|page|wp-content|wp-includes)/",
    r"/(login|logout|register|signup|signin)/",
    r"/(search|feed|rss|atom)/",
]


async def scrape_website_links(
    url: str,
    session: Optional[aiohttp.ClientSession] = None,
    max_links: int = 100,
) -> list[str]:
    """Scrape a website for article links.

    Args:
        url: Website URL to scrape
        session: Optional aiohttp session
        max_links: Maximum number of links to return

    Returns:
        List of discovered article URLs
    """
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        links = set()
        base_domain = urlparse(url).netloc

        # Try sitemap first
        sitemap_links = await _fetch_sitemap(url, session)
        if sitemap_links:
            logger.info(f"Found {len(sitemap_links)} links from sitemap")
            links.update(sitemap_links[:max_links])

        # If sitemap didn't yield enough, scrape the page
        if len(links) < max_links:
            page_links = await _scrape_page_links(url, session, base_domain)
            links.update(page_links)

        # Filter and deduplicate
        filtered = _filter_links(list(links), url)
        return filtered[:max_links]

    finally:
        if close_session:
            await session.close()


async def _fetch_sitemap(url: str, session: aiohttp.ClientSession) -> list[str]:
    """Try to fetch and parse sitemap.xml."""
    parsed = urlparse(url)
    sitemap_urls = [
        f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap-index.xml",
    ]

    for sitemap_url in sitemap_urls:
        try:
            async with session.get(sitemap_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    continue
                content = await resp.text()

                # Parse sitemap XML
                soup = BeautifulSoup(content, "html.parser")
                links = []

                # Handle sitemap index (links to other sitemaps)
                for sitemap in soup.find_all("sitemap"):
                    loc = sitemap.find("loc")
                    if loc:
                        # Could recursively fetch, but for simplicity just note it
                        logger.debug(f"Found sitemap index entry: {loc.text}")

                # Get URL entries
                for url_elem in soup.find_all("url"):
                    loc = url_elem.find("loc")
                    if loc and loc.text:
                        links.append(loc.text.strip())

                if links:
                    return links

        except Exception as e:
            logger.debug(f"Failed to fetch sitemap {sitemap_url}: {e}")

    return []


async def _scrape_page_links(
    url: str,
    session: aiohttp.ClientSession,
    base_domain: str,
) -> list[str]:
    """Scrape links from the page content."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return []
            content = await resp.text()

        soup = BeautifulSoup(content, "html.parser")
        links = set()

        # Try article-specific selectors first
        for selector in ARTICLE_SELECTORS:
            for elem in soup.select(selector):
                href = elem.get("href")
                if href:
                    full_url = urljoin(url, href)
                    if _is_same_domain(full_url, base_domain):
                        links.add(full_url)

        # If no article links found, get all links
        if not links:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                full_url = urljoin(url, href)
                if _is_same_domain(full_url, base_domain):
                    links.add(full_url)

        return list(links)

    except Exception as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return []


def _is_same_domain(url: str, base_domain: str) -> bool:
    """Check if URL is from the same domain."""
    try:
        parsed = urlparse(url)
        return parsed.netloc == base_domain or parsed.netloc.endswith(f".{base_domain}")
    except Exception:
        return False


def _filter_links(links: list[str], base_url: str) -> list[str]:
    """Filter out non-article links."""
    filtered = []
    exclude_regex = [re.compile(p, re.IGNORECASE) for p in EXCLUDE_PATTERNS]

    for link in links:
        # Must be valid URL
        if not is_valid_url(link):
            continue

        # Skip base URL itself
        if link.rstrip("/") == base_url.rstrip("/"):
            continue

        # Check exclusion patterns
        excluded = False
        for pattern in exclude_regex:
            if pattern.search(link):
                excluded = True
                break

        if not excluded:
            filtered.append(link)

    return filtered
