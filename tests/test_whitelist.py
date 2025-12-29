"""Tests for whitelist functionality."""

import pytest

from linkfeed.utils.whitelist import matches_whitelist, filter_whitelisted


class TestMatchesWhitelist:
    """Test URL matching against whitelist patterns."""

    def test_empty_whitelist_allows_all(self):
        """Empty whitelist should allow all URLs."""
        assert matches_whitelist("https://example.com", [])
        assert matches_whitelist("https://anything.com", [])

    def test_exact_domain_match(self):
        """Test exact domain matching."""
        patterns = ["example.com"]
        assert matches_whitelist("https://example.com/page", patterns)
        assert matches_whitelist("http://example.com", patterns)
        assert not matches_whitelist("https://other.com", patterns)

    def test_wildcard_subdomain(self):
        """Test wildcard subdomain patterns."""
        patterns = ["*.example.com"]
        assert matches_whitelist("https://sub.example.com", patterns)
        assert matches_whitelist("https://deep.sub.example.com", patterns)
        assert matches_whitelist("https://example.com", patterns)
        assert not matches_whitelist("https://other.com", patterns)

    def test_glob_pattern(self):
        """Test glob pattern matching."""
        patterns = ["*.youtube.com"]
        assert matches_whitelist("https://www.youtube.com/watch?v=123", patterns)
        assert matches_whitelist("https://m.youtube.com/watch?v=123", patterns)
        assert not matches_whitelist("https://vimeo.com", patterns)

    def test_multiple_patterns(self):
        """Test multiple whitelist patterns."""
        patterns = ["github.com", "*.gitlab.com", "bitbucket.org"]
        assert matches_whitelist("https://github.com/user/repo", patterns)
        assert matches_whitelist("https://gitlab.com/project", patterns)
        assert matches_whitelist("https://company.gitlab.com", patterns)
        assert matches_whitelist("https://bitbucket.org/repo", patterns)
        assert not matches_whitelist("https://example.com", patterns)

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        patterns = ["Example.COM"]
        assert matches_whitelist("https://example.com", patterns)
        assert matches_whitelist("https://EXAMPLE.COM", patterns)

    def test_url_with_port(self):
        """Test URL with port number."""
        patterns = ["localhost"]
        assert matches_whitelist("http://localhost:8000/page", patterns)

    def test_full_url_pattern(self):
        """Test matching full URL patterns."""
        patterns = ["https://example.com/api/*"]
        assert matches_whitelist("https://example.com/api/users", patterns)
        assert not matches_whitelist("https://example.com/home", patterns)

    def test_invalid_url(self):
        """Test handling of invalid URLs."""
        patterns = ["example.com"]
        assert not matches_whitelist("not a url", patterns)
        assert not matches_whitelist("", patterns)


class TestFilterWhitelisted:
    """Test filtering URLs by whitelist."""

    def test_empty_whitelist_returns_all(self):
        """Empty whitelist should return all URLs."""
        urls = [
            "https://example.com",
            "https://test.com",
            "https://other.com",
        ]
        assert filter_whitelisted(urls, []) == urls

    def test_filters_non_matching_urls(self):
        """Test filtering out non-matching URLs."""
        urls = [
            "https://github.com/user/repo",
            "https://example.com/page",
            "https://gitlab.com/project",
        ]
        patterns = ["github.com", "gitlab.com"]
        result = filter_whitelisted(urls, patterns)
        assert len(result) == 2
        assert "https://github.com/user/repo" in result
        assert "https://gitlab.com/project" in result
        assert "https://example.com/page" not in result

    def test_wildcard_filtering(self):
        """Test filtering with wildcard patterns."""
        urls = [
            "https://www.youtube.com/watch",
            "https://m.youtube.com/watch",
            "https://vimeo.com/video",
            "https://youtube.com",
        ]
        patterns = ["*.youtube.com"]
        result = filter_whitelisted(urls, patterns)
        assert len(result) == 3
        assert "https://vimeo.com/video" not in result

    def test_empty_url_list(self):
        """Test with empty URL list."""
        assert filter_whitelisted([], ["example.com"]) == []

    def test_all_urls_filtered(self):
        """Test when no URLs match whitelist."""
        urls = [
            "https://example.com",
            "https://test.com",
        ]
        patterns = ["github.com"]
        assert filter_whitelisted(urls, patterns) == []
