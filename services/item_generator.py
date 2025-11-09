from datetime import datetime
from typing import List

from pydantic import HttpUrl

from config.constants import ITEM_QUANTITY
from models.feed import JsonFeedItem, JsonFeedTopLevel
from models.query import AmazonAsinQuery, AmazonKeywordQuery, FilterableQuery
from services.url_builder import get_item_url, get_search_url
from utils.sanitize import sanitize_html


def generate_item(
    base_url: str,
    item_id: str,
    item_price_text: str,
    item_title: str | None = None,
    item_thumbnail_url: str | None = None,
) -> JsonFeedItem:
    """Generate a JsonFeedItem with structured metadata and sanitized HTML content."""
    timestamp: datetime = datetime.now()
    item_title_text: str = item_title.strip() if item_title else item_id

    # HTML components
    item_link_url: str = get_item_url(base_url, item_id)
    item_add_to_cart_url: str = (
        f"{base_url}/gp/aws/cart/add.html?ASIN.1={item_id}&Quantity.1={ITEM_QUANTITY}"
    )

    # Construct content body
    content_parts: list[str] = []
    if item_thumbnail_url:
        content_parts.append(f'<img src="{item_thumbnail_url}" />')

    content_parts.extend(
        [
            f'<p><a href="{item_link_url}">Product Link</a></p>',
            f'<p><a href="{item_add_to_cart_url}">Add to Cart</a></p>',
        ]
    )

    # Sanitize HTML
    sanitized_html: str = sanitize_html(html="".join(content_parts))

    return JsonFeedItem(
        id=timestamp.isoformat(sep="T"),
        url=HttpUrl(url=item_link_url),
        title=f"[{item_price_text}] {item_title_text}",
        content_html=sanitized_html,
        image=HttpUrl(url=item_thumbnail_url) if item_thumbnail_url else None,
        date_published=timestamp,
    )


def get_top_level_feed(
    base_url: str, query: FilterableQuery, feed_items: List[JsonFeedItem]
) -> JsonFeedTopLevel:
    """Generate a top-level JSON feed with metadata and filters."""
    # Prepare title and filters
    title_parts: list[str] = [base_url.replace("https://", ""), query.query_str]
    filters: list[str] = []

    # Add price filters
    if query.min_price:
        filters.append(f"min {query.locale.currency}{query.min_price}")
    if query.max_price:
        filters.append(f"max {query.locale.currency}{query.max_price}")

    # Add strict search filter
    if isinstance(query, AmazonKeywordQuery) and query.strict:
        filters.append("strict")

    # Append filters to title if exists
    if filters:
        title_parts.append(f"filtered by {', '.join(filters)}")

    # Determine home page URL based on query type
    if isinstance(query, AmazonKeywordQuery):
        home_page_url: str = get_search_url(base_url, query)
    elif isinstance(query, AmazonAsinQuery):
        home_page_url = get_item_url(base_url, item_id=query.query_str)
    else:
        home_page_url = base_url

    return JsonFeedTopLevel(
        version="https://jsonfeed.org/version/1.1",
        items=feed_items,
        title=" - ".join(title_parts),
        home_page_url=HttpUrl(url=home_page_url),
        favicon=HttpUrl(url=f"{base_url}/favicon.ico"),
    )
