"""Generic web page parser."""

import json
import logging
from datetime import datetime
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from openai import AsyncOpenAI
from readabilipy import simple_json_from_html_string

from linkfeed.models import Author, FeedItem
from linkfeed.parsers.base import BaseParser, register_parser
from linkfeed.utils.date_extraction import extract_date_with_llm
from linkfeed.utils.url import generate_id

logger = logging.getLogger(__name__)


@register_parser
class GenericParser(BaseParser):
    """Default parser for generic web pages."""

    priority = 0  # Lowest priority, fallback

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Generic parser can handle any URL."""
        return True

    async def parse(
        self,
        url: str,
        content: bytes,
        content_type: Optional[str],
        content_length: Optional[int] = None,
        session: Optional[aiohttp.ClientSession] = None,
        openai_client: Optional[AsyncOpenAI] = None,
    ) -> Optional[FeedItem]:
        """Parse HTML content to extract metadata."""
        try:
            # Decode content
            html_str = content.decode("utf-8", errors="replace")

            # Try ReadabiliPy first (pure Python mode, no Node.js required)
            article = self._extract_with_readability(html_str)

            if article and article.get("title"):
                return await self._build_item_from_readability(
                    url, article, html_str, openai_client
                )

            # Fall back to BeautifulSoup extraction
            return self._extract_with_beautifulsoup(url, html_str)

        except Exception as e:
            logger.debug(f"Parse error for {url}: {e}")
            return FeedItem(id=generate_id(url), url=url)

    def _extract_with_readability(self, html_str: str) -> Optional[dict]:
        """Extract article data using ReadabiliPy."""
        try:
            article = simple_json_from_html_string(html_str, use_readability=False)
            return article
        except Exception as e:
            logger.debug(f"ReadabiliPy extraction failed: {e}")
            return None

    async def _build_item_from_readability(
        self,
        url: str,
        article: dict,
        html_str: str,
        openai_client: Optional[AsyncOpenAI] = None,
    ) -> FeedItem:
        """Build FeedItem from ReadabiliPy output."""
        # Extract title
        title = article.get("title")

        # Extract author from byline
        author = None
        byline = article.get("byline")
        if byline:
            # Clean up common byline prefixes
            author = byline.strip()
            for prefix in ["By ", "by ", "BY "]:
                if author.startswith(prefix):
                    author = author[len(prefix):]
                    break

        # Extract content HTML
        content_html = article.get("plain_content")

        # Extract summary from plain_text (best paragraph from first 4)
        plain_text = article.get("plain_text")
        summary = self._extract_best_paragraph(plain_text)

        # Fall back to meta description if no summary
        if not summary:
            soup = BeautifulSoup(html_str, "html.parser")
            summary = self._extract_meta_description(soup)

        # Extract language from HTML
        soup = BeautifulSoup(html_str, "html.parser")
        language = self._extract_language(soup)

        # Extract publication date (chain fallbacks)
        logger.debug("Attempting to extract date for %s using HTML/meta.", url)
        date_published = self._extract_date(soup)
        if date_published:
            logger.debug("Date extracted from HTML/meta for %s: %s", url, date_published.isoformat())
        else:
            logger.debug("No date found in HTML/meta for %s.", url)
            if openai_client and plain_text:
                logger.debug("Attempting LLM-based date extraction for %s.", url)
            try:
                date_published = await extract_date_with_llm(plain_text, openai_client)
                if date_published:
                    logger.debug("LLM returned date for %s: %s", url, date_published.isoformat())
                else:
                    logger.debug("LLM did not return a date for %s.", url)
            except Exception as e:
                logger.debug("LLM date extraction failed for %s: %s", url, e)
            if not date_published:
                date_published = datetime.now()
                logger.debug("Falling back to current time for %s: %s", url, date_published.isoformat())

        return FeedItem(
            id=generate_id(url),
            url=url,
            title=title,
            summary=summary,
            content_html=content_html,
            date_published=date_published,
            authors=[Author(name=author)] if author else [],
            language=language,
        )

    def _extract_with_beautifulsoup(self, url: str, html_str: str) -> FeedItem:
        """Fall back to BeautifulSoup extraction."""
        soup = BeautifulSoup(html_str, "html.parser")

        title = self._extract_title(soup)
        summary = self._extract_meta_description(soup) or self._extract_first_paragraph(soup)
        author = self._extract_author(soup)
        language = self._extract_language(soup)
        date_published = self._extract_date(soup) or datetime.now()

        return FeedItem(
            id=generate_id(url),
            url=url,
            title=title,
            summary=summary,
            date_published=date_published,
            authors=[Author(name=author)] if author else [],
            language=language,
        )

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title."""
        # Try og:title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try twitter:title
        tw_title = soup.find("meta", attrs={"name": "twitter:title"})
        if tw_title and tw_title.get("content"):
            return tw_title["content"].strip()

        # Fall back to <title>
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return None

    def _extract_meta_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract description from meta tags."""
        # Try og:description
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()[:500]

        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()[:500]

        # Try twitter:description
        tw_desc = soup.find("meta", attrs={"name": "twitter:description"})
        if tw_desc and tw_desc.get("content"):
            return tw_desc["content"].strip()[:500]

        return None

    def _extract_best_paragraph(self, plain_text: Optional[list]) -> Optional[str]:
        """Extract the best paragraph from plain_text.
        
        Checks up to 4 paragraphs and returns the one with most content.
        
        Args:
            plain_text: List of paragraphs (either dicts with 'text' key or strings)
            
        Returns:
            The longest paragraph text (up to 500 chars) or None
        """
        if not plain_text or len(plain_text) == 0:
            return None
        
        # Check up to 4 paragraphs
        candidates = []
        for i, para in enumerate(plain_text[:4]):
            # Handle both dict and string formats
            if isinstance(para, dict):
                text = para.get('text', '')
            elif isinstance(para, str):
                text = para
            else:
                continue
            
            # Only consider paragraphs with meaningful content
            if text and len(text) > 100:
                candidates.append(text)
        
        # Return the longest paragraph
        if candidates:
            best = max(candidates, key=len)
            return best[:500]
        
        return None
    
    def _extract_first_paragraph(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract best paragraph from BeautifulSoup.
        
        Checks up to 4 paragraphs and returns the one with most content.
        """
        paragraphs = soup.find_all("p", limit=4)
        if not paragraphs:
            return None
        
        candidates = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 100:
                candidates.append(text)
        
        # Return the longest paragraph
        if candidates:
            best = max(candidates, key=len)
            return best[:500]
        
        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author name."""
        # Try meta author
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            return meta_author["content"].strip()

        # Try og:article:author
        og_author = soup.find("meta", property="article:author")
        if og_author and og_author.get("content"):
            return og_author["content"].strip()

        return None

    def _extract_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page language."""
        html = soup.find("html")
        if html and html.get("lang"):
            return html["lang"]

        # Try og:locale
        og_locale = soup.find("meta", property="og:locale")
        if og_locale and og_locale.get("content"):
            return og_locale["content"]

        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract publication date from various sources."""
        date_str = None

        # Try article:published_time (Open Graph)
        og_published = soup.find("meta", property="article:published_time")
        if og_published and og_published.get("content"):
            date_str = og_published["content"]

        # Try datePublished (Schema.org JSON-LD)
        if not date_str:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict):
                        date_str = data.get("datePublished") or data.get("dateCreated")
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                date_str = item.get("datePublished") or item.get("dateCreated")
                                if date_str:
                                    break
                    if date_str:
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

        # Try meta date
        if not date_str:
            meta_date = soup.find("meta", attrs={"name": "date"})
            if meta_date and meta_date.get("content"):
                date_str = meta_date["content"]

        # Try meta DC.date
        if not date_str:
            dc_date = soup.find("meta", attrs={"name": "DC.date"})
            if dc_date and dc_date.get("content"):
                date_str = dc_date["content"]

        # Try time element with datetime attribute
        if not date_str:
            time_elem = soup.find("time", attrs={"datetime": True})
            if time_elem:
                date_str = time_elem["datetime"]

        # Parse the date string
        if date_str:
            try:
                return date_parser.parse(date_str)
            except (ValueError, TypeError) as e:
                logger.debug(f"Failed to parse date '{date_str}': {e}")

        return None
