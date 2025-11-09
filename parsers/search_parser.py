from logging import Logger

from bs4 import BeautifulSoup, ResultSet
from bs4._typing import _AttributeValue
from bs4.element import Tag
from curl_cffi import Response
from stockholm import Money

from models.feed import JsonFeedItem
from models.json_ld import Product
from models.query import AmazonKeywordQuery
from services.item_generator import generate_feed_item
from services.ld_generator import generate_linked_data
from utils.price import validate_price


def parse_search_results(
    response: Response,
    query: AmazonKeywordQuery,
    base_url: str,
) -> list[JsonFeedItem | Product]:
    """
    Parse Amazon search results page and extract product details.

    Args:
        response_content (bytes): HTML content of search results
        query (AmazonKeywordQuery): Search query configuration
        base_url (str): Base URL of Amazon locale
    """
    logger: Logger = query.config.logger

    # Parse HTML
    soup: BeautifulSoup = BeautifulSoup(markup=response.content, features="html.parser")

    # Select product result divs, excluding ad holders
    results: ResultSet[Tag] = soup.select(
        selector="div.s-asin.s-result-item:not(.AdHolder)"
    )

    # Create dictionary of results by ASIN
    results_dict: dict[_AttributeValue, Tag] = {
        div["data-asin"]: div for div in results if div.get(key="data-asin")
    }

    # Strict search term filtering
    strict_terms: set[str] = (
        set(query.query_str.lower().split()) if query.strict else set()
    )

    generated_items: list[JsonFeedItem | Product] = []

    for item_id, item_soup in results_dict.items():
        # Extract product details
        title_elem: Tag | None = item_soup.select_one(selector="h2.s-line-clamp-3")
        title: str = str(title_elem["aria-label"]).strip() if title_elem else ""

        # Price extraction
        price_elem: Tag | None = item_soup.select_one(selector=".a-price .a-offscreen")

        if not price_elem:
            continue

        price: Money = validate_price(query, price_str=price_elem.text)

        # Thumbnail extraction
        thumbnail_elem: Tag | None = item_soup.find(
            attrs={"data-component-type": "s-product-image"}
        )
        thumbnail_subelem: Tag | None = (
            thumbnail_elem.select_one(selector=".s-image") if thumbnail_elem else None
        )
        thumbnail_url: _AttributeValue | None = (
            thumbnail_subelem.get(key="src")
            if thumbnail_elem and thumbnail_subelem
            else None
        )

        # Strict mode filtering
        if query.strict and strict_terms:
            if not all(term in title.lower() for term in strict_terms):
                logger.debug(msg=f"Strict mode: Skipping {item_id}")
                continue

        # Generate feed item
        try:
            if query.jsonld:
                generated_items.append(
                    generate_linked_data(
                        base_url,
                        item_id=str(item_id),
                        item_title=title,
                        item_price=price,
                        item_thumbnail_url=str(thumbnail_url),
                    )
                )
            else:
                generated_items.append(
                    generate_feed_item(
                        base_url,
                        item_id=str(item_id),
                        item_title=title,
                        item_price=price,
                        item_thumbnail_url=str(thumbnail_url),
                    )
                )
        except Exception as e:
            logger.error(msg=f"Error generating item {item_id}: {e}")

    logger.info(
        msg=f"Found {len(results_dict)} results, published {len(generated_items)} items"
    )

    return generated_items
