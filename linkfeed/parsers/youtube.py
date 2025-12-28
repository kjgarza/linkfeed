"""YouTube video parser."""

import re
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from linkfeed.models import Attachment, Author, FeedItem
from linkfeed.parsers.base import BaseParser, register_parser
from linkfeed.utils.url import generate_id


YOUTUBE_PATTERNS = [
    re.compile(r"^https?://(www\.)?youtube\.com/watch\?v=[\w-]+", re.IGNORECASE),
    re.compile(r"^https?://youtu\.be/[\w-]+", re.IGNORECASE),
    re.compile(r"^https?://(www\.)?youtube\.com/shorts/[\w-]+", re.IGNORECASE),
]


@register_parser
class YouTubeParser(BaseParser):
    """Parser for YouTube videos."""

    priority = 100  # High priority

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if URL is a YouTube video."""
        return any(pattern.match(url) for pattern in YOUTUBE_PATTERNS)

    async def parse(
        self,
        url: str,
        content: bytes,
        content_type: Optional[str],
        content_length: Optional[int] = None,
        session: Optional[aiohttp.ClientSession] = None,
        openai_client=None,
    ) -> Optional[FeedItem]:
        """Parse YouTube page to extract video metadata."""
        try:
            soup = BeautifulSoup(content, "html.parser")

            title = self._extract_title(soup)
            summary = self._extract_description(soup)
            author = self._extract_channel(soup)
            duration = self._extract_duration(soup)
            thumbnail = self._extract_thumbnail(soup, url)

            attachments = []
            if thumbnail:
                attachments.append(
                    Attachment(url=thumbnail, mime_type="image/jpeg")
                )

            return FeedItem(
                id=generate_id(url),
                url=url,
                title=title,
                summary=summary,
                authors=[Author(name=author)] if author else [],
                attachments=attachments,
                tags=["video", "youtube"],
            )
        except Exception:
            return FeedItem(
                id=generate_id(url), url=url, tags=["video", "youtube"]
            )

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract video title."""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            # Remove " - YouTube" suffix
            if title.endswith(" - YouTube"):
                title = title[:-10]
            return title

        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract video description."""
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()[:500]

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()[:500]

        return None

    def _extract_channel(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract channel name."""
        # Try link with itemprop="name"
        link = soup.find("link", itemprop="name")
        if link and link.get("content"):
            return link["content"].strip()

        # Try og:site_name (usually "YouTube")
        # Look for channel in page content
        return None

    def _extract_duration(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract video duration in seconds."""
        meta_duration = soup.find("meta", itemprop="duration")
        if meta_duration and meta_duration.get("content"):
            # Parse ISO 8601 duration (e.g., PT1H2M3S)
            duration_str = meta_duration["content"]
            return self._parse_iso_duration(duration_str)
        return None

    def _parse_iso_duration(self, duration: str) -> Optional[int]:
        """Parse ISO 8601 duration to seconds."""
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return None

    def _extract_thumbnail(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract video thumbnail URL."""
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]

        # Construct from video ID
        video_id = self._extract_video_id(url)
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

        return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from URL."""
        # youtube.com/watch?v=ID
        match = re.search(r"[?&]v=([\w-]+)", url)
        if match:
            return match.group(1)

        # youtu.be/ID
        match = re.search(r"youtu\.be/([\w-]+)", url)
        if match:
            return match.group(1)

        # youtube.com/shorts/ID
        match = re.search(r"shorts/([\w-]+)", url)
        if match:
            return match.group(1)

        return None
