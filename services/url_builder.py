from urllib.parse import quote_plus, urlencode
from models.query import AmazonAsinQuery, FilterableQuery


def get_search_url(base_url: str, query: FilterableQuery) -> str:
    """
    Generate a search URL with optional price filtering.

    Args:
        base_url: Base URL for the search engine
        query: Query object containing search parameters

    Returns:
        Fully constructed search URL
    """
    search_params: dict[str, str] = {"k": quote_plus(string=query.query_str)}

    # Handle price filtering
    if query.min_price or query.max_price:
        price_range: list[str] = [
            "p_36:",
            str(int(query.min_price * 100)) if query.min_price else "",
            "-",
            str(int(query.max_price * 100)) if query.max_price else "",
        ]
        search_params["rh"] = "".join(filter(None, price_range))

    return f"{base_url}/s?{urlencode(query=search_params)}"


def get_item_url(base_url: str, item_id: str) -> str:
    return base_url + "/gp/product/" + item_id


def get_dimension_url(base_url: str, query: AmazonAsinQuery) -> str:
    dimension_endpoint: str = (
        base_url + "/gp/product/ajax/twisterDimensionSlotsDefault?"
    )
    query_dict: dict[str, str] = {
        "asinList": query.query_str,
        "asin": query.query_str,
        "deviceType": "mobile",
    }

    return dimension_endpoint + urlencode(query=query_dict)
