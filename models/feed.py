from typing import NotRequired, TypedDict

JSONFEED_VERSION_URL = "https://jsonfeed.org/version/1.1"


class JsonFeedAuthor(TypedDict):
    name: str
    url: str
    avatar: str


class JsonFeedItem(TypedDict):
    id: str  # required
    url: NotRequired[str]
    title: NotRequired[str]
    content_html: NotRequired[str]
    content_text: NotRequired[str]
    image: NotRequired[str]
    date_published: NotRequired[str]
    date_modified: NotRequired[str]
    authors: NotRequired[list[JsonFeedAuthor]]


class JsonFeedTopLevel(TypedDict):
    title: str  # required
    items: list[JsonFeedItem]  # required
    version: str  # required
    home_page_url: NotRequired[str]
    description: NotRequired[str]
    favicon: NotRequired[str]
    authors: NotRequired[list[JsonFeedAuthor]]
