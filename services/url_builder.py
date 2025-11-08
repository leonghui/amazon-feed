from urllib.parse import quote_plus, urlencode
from models.query import AmazonLocale, FilterableQuery, AmazonAsinQuery


def get_search_url(base_url: str, query: FilterableQuery) -> str:
    search_uri: str = f"{base_url}/s?"

    search_dict: dict[str, str] = {"k": quote_plus(string=query.query_str)}

    price_param_value = min_price = max_price = None

    if query.min_price or query.max_price:
        price_param = "p_36:"
        if query.min_price:
            min_price = query.min_price + "00"
        if query.max_price:
            max_price = query.max_price + "00"

        price_param_value: str = "".join(
            item for item in [price_param, min_price, "-", max_price] if item
        )

    if price_param_value:
        search_dict["rh"] = price_param_value

    return search_uri + urlencode(query=search_dict)


def get_item_url(base_url: str, item_id: str) -> str:
    return base_url + "/gp/product/" + item_id


def get_dimension_url(query: AmazonAsinQuery) -> str:
    locale_data: AmazonLocale = query.locale
    base_url: str = "https://" + locale_data.domain
    dimension_endpoint: str = base_url + "/gp/product/ajax?"

    query_dict: dict[str, str] = {
        "asinList": query.query_str,
        "experienceId": "twisterDimensionSlotsDefault",
        "asin": query.query_str,
        "deviceType": "mobile",
    }

    return dimension_endpoint + urlencode(query=query_dict)
