from dataclasses import dataclass, field

JSONFEED_VERSION_URL = 'https://jsonfeed.org/version/1.1'


@dataclass
class JsonFeedAuthor():
    name: str = None
    url: str = None
    avatar: str = None


@dataclass
class JsonFeedItem():
    id: str  # required
    url: str = None
    title: str = None
    content_html: str = None
    image: str = None
    date_published: str = None
    authors: list[JsonFeedAuthor] = field(default_factory=list)


@dataclass
class JsonFeedTopLevel():
    title: str  # required
    items: list[JsonFeedItem]  # required
    version: str = JSONFEED_VERSION_URL  # required
    home_page_url: str = None
    description: str = None
    favicon: str = None
    authors: list[JsonFeedAuthor] = field(default_factory=list)
