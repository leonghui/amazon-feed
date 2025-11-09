from logging import Logger

from models.feed import JsonFeedItem
from models.query import AmazonAsinQuery
from services.item_generator import generate_item


def parse_item_details(
    json_dict: dict, query: AmazonAsinQuery, base_url: str
) -> list[JsonFeedItem]:
    logger: Logger = query.config.logger

    try:
        # Navigate nested JSON structure
        price_data = (
            json_dict.get("Value", {}).get("content", {}).get("twisterSlotJson", {})
        )

        # Extract price
        price_str = price_data.get("price")

        if not price_str:
            logger.error(msg=f"{query.query_str} - Price not found")
            return []

        # Price validation and filtering
        price: float = float(price_str)

        # Check against max price if specified
        if query.max_price and price > float(query.max_price):
            logger.info(msg=f"{query.query_str} - Exceeded max price {query.max_price}")
            return []

        # Format price with currency
        formatted_price: str = f"{query.locale.currency}{price:.2f}"

        generated_items: list[JsonFeedItem] = []

        generated_items.append(
            generate_item(
                base_url,
                item_id=query.query_str,
                item_price_text=formatted_price,
            )
        )

        return generated_items

    except Exception as e:
        logger.error(msg=f"{query.query_str} - Parsing error: {e}")
        return []
