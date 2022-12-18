from typing import List, TypedDict

JSONFEED_VERSION_URL = 'https://jsonfeed.org/version/1.1'


class JsonFeedAuthor(TypedDict):
    name: str
    url: str
    avatar: str


class JsonFeedItem(TypedDict):
    id: str  # required
    url: str
    title: str
    content_html: str
    content_text: str
    image: str
    date_published: str
    date_modified: str
    authors: List[JsonFeedAuthor]


class JsonFeedTopLevel(TypedDict):
    title: str  # required
    items: List[JsonFeedItem]  # required
    version: str  # required
    home_page_url: str
    description: str
    favicon: str
    authors: List[JsonFeedAuthor]
