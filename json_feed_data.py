from dataclasses import dataclass

JSONFEED_VERSION_URL = 'https://jsonfeed.org/version/1.1'


@dataclass
class JsonFeedItem():
    id: str = None
    url: str = None
    title: str = None
    content_html: str = None
    content_body: str = None
    image: str = None
    date_published: str = None


@dataclass
class JsonFeedTopLevel():
    items: list[JsonFeedItem]
    version: str = JSONFEED_VERSION_URL
    title: str = None
    home_page_url: str = None
    favicon: str = None

