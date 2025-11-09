from datetime import datetime
from typing import Annotated, TypeAlias
from pydantic import BaseModel, HttpUrl, PlainSerializer

JSONFEED_VERSION_URL = "https://jsonfeed.org/version/1.1"


def serialize_httpurl(obj: HttpUrl) -> str:
    return str(obj)


def serialize_datetime_rfc3339(obj: datetime) -> str:
    return obj.isoformat(sep="T")


SerHttpUrl: TypeAlias = Annotated[HttpUrl, PlainSerializer(func=serialize_httpurl)]

Rfc3339DateTime: TypeAlias = Annotated[
    datetime, PlainSerializer(func=serialize_datetime_rfc3339)
]


class JsonFeedItemAttachment(BaseModel):
    url: SerHttpUrl  # required
    mime_type: str  # required
    title: str | None = None
    size_in_bytes: int | None = None
    duration_in_bytes: int | None = None


class JsonFeedAuthor(BaseModel):
    name: str | None = None
    url: SerHttpUrl | None = None
    avatar: str | None = None


class JsonFeedItem(BaseModel):
    id: str  # required
    url: SerHttpUrl | None = None
    external_url: SerHttpUrl | None = None
    title: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    summary: str | None = None
    image: SerHttpUrl | None = None
    banner_image: SerHttpUrl | None = None
    date_published: Rfc3339DateTime | None = None
    date_modified: Rfc3339DateTime | None = None
    authors: list[JsonFeedAuthor] | None = None
    tags: list[str] | None = None
    language: str | None = None
    attachments: list[JsonFeedItemAttachment] | None = None


class JsonFeedTopLevel(BaseModel):
    version: str  # required
    title: str  # required
    home_page_url: SerHttpUrl | None = None
    feed_url: SerHttpUrl | None = None
    description: str | None = None
    user_comment: str | None = None
    next_url: SerHttpUrl | None = None
    icon: SerHttpUrl | None = None
    favicon: SerHttpUrl | None = None
    authors: list[JsonFeedAuthor] | None = None
    language: str | None = None
    expired: bool | None = None
    items: list[JsonFeedItem]  # required
