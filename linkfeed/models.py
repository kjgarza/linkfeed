"""Data models for linkfeed."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """Represents a media attachment in a feed item."""

    url: str
    mime_type: str
    size_in_bytes: Optional[int] = None
    duration_in_seconds: Optional[int] = None


class Author(BaseModel):
    """Represents an author in the feed."""

    name: Optional[str] = None
    url: Optional[str] = None


class FeedItem(BaseModel):
    """Represents an item in the feed."""

    id: str
    url: str
    title: Optional[str] = None
    summary: Optional[str] = None
    content_html: Optional[str] = None
    date_published: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    authors: list[Author] = Field(default_factory=list)
    language: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)

    def to_json_feed_item(self) -> dict:
        """Convert to JSON Feed v1 item format."""
        item = {"id": self.id, "url": self.url}

        if self.title:
            item["title"] = self.title
        if self.summary:
            item["summary"] = self.summary
        if self.content_html:
            item["content_html"] = self.content_html
        if self.date_published:
            item["date_published"] = self.date_published.isoformat()
        if self.date_modified:
            item["date_modified"] = self.date_modified.isoformat()
        if self.authors:
            item["authors"] = [
                {k: v for k, v in a.model_dump().items() if v is not None}
                for a in self.authors
            ]
        if self.language:
            item["language"] = self.language
        if self.tags:
            item["tags"] = self.tags
        if self.attachments:
            item["attachments"] = [
                {k: v for k, v in a.model_dump().items() if v is not None}
                for a in self.attachments
            ]

        return item


class Feed(BaseModel):
    """Represents a JSON Feed."""

    version: str = "https://jsonfeed.org/version/1.1"
    title: str
    home_page_url: Optional[str] = None
    feed_url: Optional[str] = None
    description: Optional[str] = None
    authors: list[Author] = Field(default_factory=list)
    language: Optional[str] = None
    items: list[FeedItem] = Field(default_factory=list)

    def to_json_feed(self) -> dict:
        """Convert to JSON Feed v1 format."""
        feed = {"version": self.version, "title": self.title}

        if self.home_page_url:
            feed["home_page_url"] = self.home_page_url
        if self.feed_url:
            feed["feed_url"] = self.feed_url
        if self.description:
            feed["description"] = self.description
        if self.authors:
            feed["authors"] = [
                {k: v for k, v in a.model_dump().items() if v is not None}
                for a in self.authors
            ]
        if self.language:
            feed["language"] = self.language

        feed["items"] = [item.to_json_feed_item() for item in self.items]

        return feed

    @classmethod
    def from_json_feed(cls, data: dict) -> "Feed":
        """Create a Feed from JSON Feed data."""
        items = []
        for item_data in data.get("items", []):
            # Parse dates back to datetime
            if "date_published" in item_data and item_data["date_published"]:
                item_data["date_published"] = datetime.fromisoformat(
                    item_data["date_published"].replace("Z", "+00:00")
                )
            if "date_modified" in item_data and item_data["date_modified"]:
                item_data["date_modified"] = datetime.fromisoformat(
                    item_data["date_modified"].replace("Z", "+00:00")
                )
            items.append(FeedItem(**item_data))

        authors = [Author(**a) for a in data.get("authors", [])]

        return cls(
            version=data.get("version", "https://jsonfeed.org/version/1.1"),
            title=data.get("title", "Untitled Feed"),
            home_page_url=data.get("home_page_url"),
            feed_url=data.get("feed_url"),
            description=data.get("description"),
            authors=authors,
            language=data.get("language"),
            items=items,
        )
