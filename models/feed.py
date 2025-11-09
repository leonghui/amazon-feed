from pydantic import BaseModel

JSONFEED_VERSION_URL = "https://jsonfeed.org/version/1.1"


class JsonFeedAuthor(BaseModel):
    name: str
    url: str
    avatar: str


class JsonFeedItem(BaseModel):
    id: str  # required
    url: str | None = None
    title: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    image: str | None = None
    date_published: str | None = None
    date_modified: str | None = None
    authors: list[JsonFeedAuthor] | None = None


class JsonFeedTopLevel(BaseModel):
    title: str  # required
    items: list[JsonFeedItem]  # required
    version: str  # required
    home_page_url: str | None = None
    description: str | None = None
    favicon: str | None = None
    authors: list[JsonFeedAuthor] | None = None
