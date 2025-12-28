"""Media file parser for direct media URLs."""

from typing import Optional
from urllib.parse import unquote, urlparse

import aiohttp

from linkfeed.models import Attachment, FeedItem
from linkfeed.parsers.base import BaseParser, register_parser
from linkfeed.utils.url import generate_id


MEDIA_EXTENSIONS = {
    # Audio
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    # Video
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    # Documents
    ".pdf": "application/pdf",
}

MEDIA_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp4",
    "audio/ogg",
    "audio/wav",
    "audio/flac",
    "audio/aac",
    "video/mp4",
    "video/webm",
    "video/x-matroska",
    "video/quicktime",
    "application/pdf",
}


@register_parser
class MediaParser(BaseParser):
    """Parser for direct media file URLs."""

    priority = 50  # Medium priority

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if URL points to a media file."""
        url_lower = url.lower()

        # Check file extension
        for ext in MEDIA_EXTENSIONS:
            if url_lower.endswith(ext) or f"{ext}?" in url_lower:
                return True

        return False

    async def parse(
        self,
        url: str,
        content: bytes,
        content_type: Optional[str],
        content_length: Optional[int] = None,
        session: Optional[aiohttp.ClientSession] = None,
        openai_client=None,
    ) -> Optional[FeedItem]:
        """Create a feed item for a media file."""
        # Determine MIME type
        mime_type = self._detect_mime_type(url, content_type)

        # Use content_length from fetch result (no need for separate HEAD request)
        size = content_length

        # Extract filename for title
        title = self._extract_filename(url)

        # Determine tags based on type
        tags = []
        if mime_type:
            if mime_type.startswith("audio/"):
                tags.append("audio")
            elif mime_type.startswith("video/"):
                tags.append("video")
            elif mime_type == "application/pdf":
                tags.append("pdf")

        attachment = Attachment(
            url=url,
            mime_type=mime_type or "application/octet-stream",
            size_in_bytes=size,
        )

        return FeedItem(
            id=generate_id(url),
            url=url,
            title=title,
            attachments=[attachment],
            tags=tags,
        )

    def _detect_mime_type(
        self, url: str, content_type: Optional[str]
    ) -> Optional[str]:
        """Detect MIME type from URL or content type header."""
        # First check content-type header
        if content_type:
            # Extract main type (ignore charset, etc.)
            main_type = content_type.split(";")[0].strip().lower()
            if main_type in MEDIA_CONTENT_TYPES:
                return main_type

        # Fall back to extension
        url_lower = url.lower()
        for ext, mime in MEDIA_EXTENSIONS.items():
            if url_lower.endswith(ext) or f"{ext}?" in url_lower:
                return mime

        return None

    def _extract_filename(self, url: str) -> Optional[str]:
        """Extract filename from URL for use as title."""
        parsed = urlparse(url)
        path = unquote(parsed.path)

        # Get last path segment
        if "/" in path:
            filename = path.rsplit("/", 1)[-1]
            # Remove query string if present
            if "?" in filename:
                filename = filename.split("?")[0]
            return filename if filename else None

        return None
