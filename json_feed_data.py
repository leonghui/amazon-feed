from dataclasses import dataclass

JSONFEED_VERSION_URL = 'https://jsonfeed.org/version/1.1'


@dataclass
class JsonFeedItem():
    id: str = ''  # required
    url: str = None
    title: str = None
    content_html: str = None
    image: str = None
    date_published: str = None


@dataclass
class JsonFeedTopLevel():
    items: list[JsonFeedItem]  # required
    version: str = JSONFEED_VERSION_URL  # required
    title: str = ''  # required
    home_page_url: str = None
    favicon: str = None
