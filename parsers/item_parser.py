from logging import Logger

from curl_cffi import Response
from stockholm import Money

from models.feed import JsonFeedItem
from models.json_ld import Product
from models.query import AmazonAsinQuery
from services.item_generator import generate_feed_item
from services.ld_generator import generate_linked_data
from utils.price import validate_price


def parse_item_details(
    response: Response, query: AmazonAsinQuery, base_url: str
) -> list[JsonFeedItem | Product]:
    logger: Logger = query.config.logger

    try:
        # Navigate nested JSON structure
        price_data = (
            response.json().get("Value", {}).get("content", {}).get("twisterSlotJson", {})
        )

        # Extract price
        price_flt: float = price_data.get("price")

        if not price_flt:
            logger.error(msg=f"{query.query_str} - Price not found")
            return []

        price: Money = validate_price(query, str(price_flt))

        # Check against max price if specified
        if query.max_price and price > float(query.max_price):
            logger.info(msg=f"{query.query_str} - Exceeded max price {query.max_price}")
            return []

        generated_items: list[JsonFeedItem | Product] = []

        if query.jsonld:
            generated_items.append(
                generate_linked_data(
                    base_url,
                    item_id=query.query_str,
                    item_price=price,
                )
            )
        else:
            generated_items.append(
                generate_feed_item(
                    base_url,
                    item_id=query.query_str,
                    item_price=price,
                )
            )

        return generated_items

    except Exception as e:
        logger.error(msg=f"{query.query_str} - Parsing error: {e}")
        return []
