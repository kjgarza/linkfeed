"""URL utilities for canonicalization and ID generation."""

import hashlib
import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


# Common tracking parameters to remove
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "source",
    "mc_cid",
    "mc_eid",
}


def canonicalize_url(url: str) -> str:
    """Normalize a URL by removing tracking parameters and standardizing format."""
    try:
        parsed = urlparse(url)

        # Lowercase scheme and host
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default ports
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]

        # Remove trailing slash from path (unless it's just "/")
        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        # Filter out tracking parameters
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMS
        }

        # Sort parameters for consistency
        sorted_query = urlencode(filtered_params, doseq=True) if filtered_params else ""

        # Remove fragment
        return urlunparse((scheme, netloc, path, "", sorted_query, ""))
    except Exception:
        return url


def generate_id(url: str) -> str:
    """Generate a deterministic ID from a canonical URL using SHA256."""
    canonical = canonicalize_url(url)
    hash_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    # Use first 16 characters for reasonable length while maintaining uniqueness
    return hash_digest[:16]


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP(S) URL."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


class URLDeduplicator:
    """Track seen URLs to prevent duplicates."""

    def __init__(self):
        self._seen_ids: set[str] = set()

    def add_existing_ids(self, ids: list[str]) -> None:
        """Add existing IDs from a feed."""
        self._seen_ids.update(ids)

    def is_duplicate(self, url: str) -> bool:
        """Check if a URL has already been seen."""
        url_id = generate_id(url)
        return url_id in self._seen_ids

    def mark_seen(self, url: str) -> str:
        """Mark a URL as seen and return its ID."""
        url_id = generate_id(url)
        self._seen_ids.add(url_id)
        return url_id
