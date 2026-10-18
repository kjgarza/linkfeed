"""qurl source: read URLs from a local qurl SQLite store."""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

from linkfeed.sources.base import BaseSource, register_source

logger = logging.getLogger(__name__)

DEFAULT_QURL_DB = "~/.cache/qurl/qurl.sqlite"


def default_qurl_db() -> str:
    """Resolve the qurl database path the same way the qurl CLI does."""
    return os.environ.get("QURL_DB_PATH") or DEFAULT_QURL_DB


@register_source("qurl")
class QurlSource(BaseSource):
    """Fetch document URLs from a qurl store, newest first."""

    def __init__(
        self,
        db: Optional[str] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> None:
        self.db = Path(db or default_qurl_db()).expanduser()
        self.source = source
        self.limit = limit

    async def fetch_urls(self) -> list[str]:
        """Return active http(s) document URLs, optionally filtered by qurl source."""
        if not self.db.exists():
            logger.warning(f"qurl database not found: {self.db}")
            return []

        query = (
            "SELECT url FROM documents WHERE active = 1 "
            "AND (url LIKE 'http://%' OR url LIKE 'https://%')"
        )
        params: list = []
        if self.source:
            query += " AND source = ?"
            params.append(self.source)
        query += " ORDER BY created_at DESC"
        if self.limit:
            query += " LIMIT ?"
            params.append(self.limit)

        try:
            conn = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
            try:
                rows = conn.execute(query, params).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.warning(f"Error reading qurl database {self.db}: {e}")
            return []

        return [row[0] for row in rows]
