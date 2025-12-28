"""Blacklist filtering for URLs."""

import fnmatch
from urllib.parse import urlparse


def matches_blacklist(url: str, patterns: list[str]) -> bool:
    """Check if a URL matches any blacklist pattern."""
    if not patterns:
        return False

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]

        for pattern in patterns:
            pattern = pattern.lower().strip()

            # Handle *.domain.com patterns
            if pattern.startswith("*."):
                base_domain = pattern[2:]
                if domain == base_domain or domain.endswith("." + base_domain):
                    return True
            # Handle exact domain matches
            elif fnmatch.fnmatch(domain, pattern):
                return True
            # Handle full URL pattern matching
            elif fnmatch.fnmatch(url.lower(), pattern):
                return True

        return False
    except Exception:
        return False


def filter_blacklisted(urls: list[str], patterns: list[str]) -> list[str]:
    """Filter out URLs that match blacklist patterns."""
    return [url for url in urls if not matches_blacklist(url, patterns)]
