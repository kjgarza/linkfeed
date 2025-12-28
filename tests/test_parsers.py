"""Tests for parsers."""

import pytest
from linkfeed.parsers.base import get_parser
from linkfeed.parsers.youtube import YouTubeParser
from linkfeed.parsers.media import MediaParser
from linkfeed.parsers.generic import GenericParser


class TestParserRegistry:
    def test_youtube_parser_priority(self):
        parser = get_parser("https://youtube.com/watch?v=abc123")
        assert isinstance(parser, YouTubeParser)

    def test_youtube_short_url(self):
        parser = get_parser("https://youtu.be/abc123")
        assert isinstance(parser, YouTubeParser)

    def test_media_parser_mp3(self):
        parser = get_parser("https://example.com/audio.mp3")
        assert isinstance(parser, MediaParser)

    def test_media_parser_pdf(self):
        parser = get_parser("https://example.com/doc.pdf")
        assert isinstance(parser, MediaParser)

    def test_generic_fallback(self):
        parser = get_parser("https://example.com/article")
        assert isinstance(parser, GenericParser)


class TestGenericParser:
    @pytest.mark.asyncio
    async def test_extracts_title(self):
        parser = GenericParser()
        html = b"""
        <html>
        <head><title>Test Title</title></head>
        <body></body>
        </html>
        """
        item = await parser.parse("https://example.com", html, "text/html")
        assert item.title == "Test Title"

    @pytest.mark.asyncio
    async def test_extracts_og_title(self):
        parser = GenericParser()
        html = b"""
        <html>
        <head>
            <meta property="og:title" content="OG Title">
            <title>Regular Title</title>
        </head>
        </html>
        """
        item = await parser.parse("https://example.com", html, "text/html")
        assert item.title == "OG Title"

    @pytest.mark.asyncio
    async def test_extracts_description(self):
        parser = GenericParser()
        html = b"""
        <html>
        <head>
            <meta name="description" content="Page description">
        </head>
        </html>
        """
        item = await parser.parse("https://example.com", html, "text/html")
        assert item.summary == "Page description"


class TestYouTubeParser:
    def test_can_handle_watch_url(self):
        assert YouTubeParser.can_handle("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert YouTubeParser.can_handle("https://youtube.com/watch?v=dQw4w9WgXcQ")

    def test_can_handle_short_url(self):
        assert YouTubeParser.can_handle("https://youtu.be/dQw4w9WgXcQ")

    def test_can_handle_shorts(self):
        assert YouTubeParser.can_handle("https://youtube.com/shorts/abc123")

    def test_not_handle_channel(self):
        assert not YouTubeParser.can_handle("https://youtube.com/channel/xyz")


class TestMediaParser:
    def test_can_handle_mp3(self):
        assert MediaParser.can_handle("https://example.com/audio.mp3")

    def test_can_handle_pdf(self):
        assert MediaParser.can_handle("https://example.com/doc.pdf")

    def test_can_handle_mp4(self):
        assert MediaParser.can_handle("https://example.com/video.mp4")

    def test_not_handle_html(self):
        assert not MediaParser.can_handle("https://example.com/page.html")

    @pytest.mark.asyncio
    async def test_extracts_filename(self):
        parser = MediaParser()
        item = await parser.parse(
            "https://example.com/podcast-ep1.mp3", b"", "audio/mpeg", 1024
        )
        assert item.title == "podcast-ep1.mp3"
        assert len(item.attachments) == 1
        assert item.attachments[0].mime_type == "audio/mpeg"
        assert item.attachments[0].size_in_bytes == 1024
