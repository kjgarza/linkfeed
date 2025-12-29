"""Whitelist filtering for URLs."""

import fnmatch
from urllib.parse import urlparse


def matches_whitelist(url: str, patterns: list[str]) -> bool:
    """Check if a URL matches any whitelist pattern."""
    if not patterns:
        return True  # No whitelist means all URLs allowed

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


def filter_whitelisted(urls: list[str], patterns: list[str]) -> list[str]:
    """Filter URLs to only those that match whitelist patterns."""
    if not patterns:
        return urls  # No whitelist means all URLs allowed
    return [url for url in urls if matches_whitelist(url, patterns)]
