"""Tests for URL utilities."""

import pytest
from linkfeed.utils.url import (
    canonicalize_url,
    generate_id,
    is_valid_url,
    extract_domain,
    URLDeduplicator,
)


class TestCanonicalizeUrl:
    def test_removes_tracking_params(self):
        url = "https://example.com/page?utm_source=twitter&id=123"
        result = canonicalize_url(url)
        assert "utm_source" not in result
        assert "id=123" in result

    def test_lowercase_host(self):
        url = "https://EXAMPLE.COM/Page"
        result = canonicalize_url(url)
        assert result.startswith("https://example.com")

    def test_removes_trailing_slash(self):
        url = "https://example.com/page/"
        result = canonicalize_url(url)
        assert result == "https://example.com/page"

    def test_keeps_root_slash(self):
        url = "https://example.com/"
        result = canonicalize_url(url)
        assert result == "https://example.com/"

    def test_removes_fragment(self):
        url = "https://example.com/page#section"
        result = canonicalize_url(url)
        assert "#" not in result


class TestGenerateId:
    def test_deterministic(self):
        url = "https://example.com/article"
        id1 = generate_id(url)
        id2 = generate_id(url)
        assert id1 == id2

    def test_different_urls_different_ids(self):
        id1 = generate_id("https://example.com/a")
        id2 = generate_id("https://example.com/b")
        assert id1 != id2

    def test_canonicalizes_before_hashing(self):
        id1 = generate_id("https://example.com/page")
        id2 = generate_id("https://example.com/page?utm_source=x")
        assert id1 == id2


class TestIsValidUrl:
    def test_valid_https(self):
        assert is_valid_url("https://example.com")

    def test_valid_http(self):
        assert is_valid_url("http://example.com")

    def test_invalid_scheme(self):
        assert not is_valid_url("ftp://example.com")

    def test_relative_path(self):
        assert not is_valid_url("./page.html")

    def test_file_path(self):
        assert not is_valid_url("file:///home/user/file.txt")


class TestExtractDomain:
    def test_simple_domain(self):
        assert extract_domain("https://example.com/page") == "example.com"

    def test_with_subdomain(self):
        assert extract_domain("https://www.example.com") == "www.example.com"


class TestURLDeduplicator:
    def test_marks_as_seen(self):
        dedup = URLDeduplicator()
        url = "https://example.com/article"
        assert not dedup.is_duplicate(url)
        dedup.mark_seen(url)
        assert dedup.is_duplicate(url)

    def test_existing_ids(self):
        dedup = URLDeduplicator()
        existing_id = generate_id("https://example.com/old")
        dedup.add_existing_ids([existing_id])
        assert dedup.is_duplicate("https://example.com/old")


# Tests for Trello parsing
from linkfeed.utils.trello import extract_urls_from_text, parse_trello_card


class TestTrelloExtractUrls:
    def test_extracts_bare_url(self):
        text = "Check out https://example.com/article for more info"
        urls = extract_urls_from_text(text)
        assert "https://example.com/article" in urls

    def test_extracts_multiple_urls(self):
        text = "See https://example.com and https://test.org/page"
        urls = extract_urls_from_text(text)
        assert len(urls) == 2
        assert "https://example.com" in urls
        assert "https://test.org/page" in urls

    def test_filters_trello_urls(self):
        text = "Card at https://trello.com/c/abc123 links to https://example.com"
        urls = extract_urls_from_text(text)
        assert len(urls) == 1
        assert "https://example.com" in urls
        assert not any("trello.com" in u for u in urls)

    def test_handles_empty_text(self):
        assert extract_urls_from_text("") == []
        assert extract_urls_from_text(None) == []

    def test_strips_trailing_punctuation(self):
        text = "Visit https://example.com/page."
        urls = extract_urls_from_text(text)
        assert "https://example.com/page" in urls


class TestTrelloParseCard:
    def test_extracts_from_name(self):
        card = {
            "name": "Article | https://example.com/article",
            "desc": "",
        }
        urls = parse_trello_card(card)
        assert "https://example.com/article" in urls

    def test_extracts_from_desc(self):
        card = {
            "name": "My card",
            "desc": "Check https://example.com for details",
        }
        urls = parse_trello_card(card)
        assert "https://example.com" in urls

    def test_extracts_from_both(self):
        card = {
            "name": "Link: https://example.com/a",
            "desc": "Also see https://example.com/b",
        }
        urls = parse_trello_card(card)
        assert len(urls) == 2

    def test_handles_missing_fields(self):
        card = {"id": "123"}
        urls = parse_trello_card(card)
        assert urls == []


# Tests for tag parsing
from linkfeed.utils.tagging import parse_tags


class TestTagParsing:
    def test_parses_simple_tags(self):
        raw = "technology\nai\nmachine-learning"
        tags = parse_tags(raw)
        assert tags == ["technology", "ai", "machine-learning"]

    def test_removes_numbering(self):
        raw = "1. technology\n2. ai\n3. science"
        tags = parse_tags(raw)
        assert tags == ["technology", "ai", "science"]

    def test_removes_bullets(self):
        raw = "- technology\n* ai\n• science"
        tags = parse_tags(raw)
        assert tags == ["technology", "ai", "science"]

    def test_takes_first_word(self):
        raw = "machine learning\nartificial intelligence"
        tags = parse_tags(raw)
        assert tags == ["machine", "artificial"]

    def test_lowercases(self):
        raw = "Technology\nAI\nScience"
        tags = parse_tags(raw)
        assert tags == ["technology", "ai", "science"]

    def test_limits_to_five(self):
        raw = "tech\nai\nscience\ndata\nml\ncloud\nweb"
        tags = parse_tags(raw)
        assert len(tags) == 5

    def test_deduplicates(self):
        raw = "tech\ntech\nai\nai"
        tags = parse_tags(raw)
        assert tags == ["tech", "ai"]
