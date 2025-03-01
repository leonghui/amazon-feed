import re
from datetime import datetime
from urllib.parse import quote_plus, urlencode, urlparse

import nh3
from bs4 import BeautifulSoup
from flask import abort
from requests.exceptions import JSONDecodeError, RequestException
from requests_cache import AnyResponse

from amazon_feed_data import (
    BOT_PATTERN,
    AmazonAsinQuery,
    AmazonKeywordQuery,
    FilterableQuery,
)
from json_feed_data import JSONFEED_VERSION_URL, JsonFeedItem, JsonFeedTopLevel

ITEM_QUANTITY = 1

allowed_tags = {"a", "img", "p"}
allowed_attributes = {"a": {"href", "title"}, "img": {"src"}}
STREAM_DELIMITER = "&&&"  # application/json-amazonui-streaming

# mimic headers from Android app
headers = {
    "Accept": "text/html,*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "device-memory": "8",
    "downlink": "9.3",
    "dpr": "2",
    "ect": "4g",
    "Referer": "https://www.amazon.com/",
    "rtt": "0",
    "sec-ch-device-memory": "8",
    "sec-ch-dpr": "2",
    "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Android WebView";v="128"',
    "sec-ch-ua-mobile": '?1',
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua-platform-version": '""',
    "sec-ch-viewport-width": "393",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "viewport-width": "393"

}


def clear_session_cookies(query: FilterableQuery):
    query.config.session.cookies.clear()


def handle_response(response: AnyResponse, query: FilterableQuery):
    logger = query.config.logger

    try:
        return response.json()
    except JSONDecodeError as jdex:
        logger.debug(f"{query.query_str} - {type(jdex)}: {jdex}")
        logger.debug(f"{query.query_str} - dumping response: {response.text}")
        return None


def get_response_dict(url: str, query: FilterableQuery):
    logger = query.config.logger
    session = query.config.session

    headers["User-Agent"] = query.config.useragent
    headers["Referer"] = "https://" + query.locale.domain + "/"

    session.headers = headers

    logger.debug(f"{query.query_str} - querying endpoint: {url}")

    try:
        response = session.get(url)
    except RequestException as rex:
        clear_session_cookies(query)
        logger.error(f"{query.query_str} - {type(rex)}: {rex}")
        return None

    # return HTTP error code
    if not response.ok:
        if response.status_code == 503 or re.search(BOT_PATTERN, response.text):
            bot_msg = f"{query.query_str} - API paywall triggered, resetting session"
            clear_session_cookies(query)

            logger.warning(bot_msg)
            abort(429, description=bot_msg)
        else:
            logger.error(f"{query.query_str} - error from source")
            logger.debug(f"{query.query_str} - dumping response: {response.text}")
            return None
    else:
        logger.debug(f"{query.query_str} - response cached: {response.from_cache}")

    return handle_response(response, query)


def get_search_url(base_url: str, query: FilterableQuery, is_xhr: bool = True):
    search_uri = f"{base_url}/s/query?" if is_xhr else f"{base_url}/s?"

    search_dict = {"k": quote_plus(query.query_str)}

    price_param_value = min_price = max_price = None

    if query.min_price or query.max_price:
        price_param = "p_36:"
        if query.min_price:
            min_price = query.min_price + "00"
        if query.max_price:
            max_price = query.max_price + "00"

        price_param_value = "".join(
            item for item in [price_param, min_price, "-", max_price] if item
        )

    if price_param_value:
        search_dict["rh"] = price_param_value

    return search_uri + urlencode(search_dict)


def get_item_url(base_url: str, item_id: str):
    return base_url + "/gp/product/" + item_id


def get_top_level_feed(
    base_url: str, query: FilterableQuery, feed_items: list[JsonFeedItem]
):
    parse_object = urlparse(base_url)
    domain = parse_object.netloc

    title_strings = [domain, query.query_str]

    filters = []

    if isinstance(query, AmazonKeywordQuery):
        home_page_url = get_search_url(base_url, query, is_xhr=False)

        if query.strict:
            filters.append("strict")

    elif isinstance(query, AmazonAsinQuery):
        home_page_url = get_item_url(base_url, query.query_str)

    if query.min_price:
        filters.append(f"min {query.locale.currency}{query.min_price}")

    if query.max_price:
        filters.append(f"max {query.locale.currency}{query.max_price}")

    if filters:
        title_strings.append(f"filtered by {', '.join(filters)}")

    json_feed = JsonFeedTopLevel(
        version=JSONFEED_VERSION_URL,
        items=feed_items,
        title=" - ".join(title_strings),
        home_page_url=home_page_url,
        favicon=base_url + "/favicon.ico",
    )

    return json_feed


def generate_item(
    base_url: str,
    item_id: str,
    item_title: str,
    item_price_text: str,
    item_thumbnail_url: str,
):
    item_title_text = item_title.strip() if item_title else item_id

    item_thumbnail_html = f'<img src="{item_thumbnail_url}" />'

    timestamp = datetime.now().timestamp()

    item_link_url = get_item_url(base_url, item_id)
    item_link_html = f'<p><a href="{item_link_url}">Product Link</a></p>'

    item_add_to_cart_url = (
        f"{base_url}/gp/aws/cart/add.html?ASIN.1={item_id}&Quantity.1={ITEM_QUANTITY}"
    )
    item_add_to_cart_html = f'<p><a href="{item_add_to_cart_url}">Add to Cart</a></p>'

    content_body_list = [item_link_html, item_add_to_cart_html]

    if item_thumbnail_url:
        content_body_list.insert(0, item_thumbnail_html)

    content_body = "".join(content_body_list)

    sanitized_html = nh3.clean(
        content_body, tags=allowed_tags, attributes=allowed_attributes
    ).replace(
        "&amp;", "&"
    )  # restore raw ampersands: https://github.com/mozilla/bleach/issues/192

    feed_item = JsonFeedItem(
        id=datetime.utcfromtimestamp(timestamp).isoformat("T"),
        url=item_link_url,
        title=f"[{item_price_text}] {item_title_text}",
        content_html=sanitized_html,
        image=item_thumbnail_url,
        date_published=datetime.utcfromtimestamp(timestamp).isoformat("T"),
    )

    return feed_item


def get_keyword_results(search_query: AmazonKeywordQuery):
    logger = search_query.config.logger

    base_url = "https://" + search_query.locale.domain

    search_url = get_search_url(base_url, search_query)

    json_dict = get_response_dict(search_url, search_query)

    results_dict = (
        {
            k: v
            for k, v in json_dict.items()
            if k.startswith("data-main-slot:search-result-")
        }
        if json_dict
        else {}
    )

    term_list: list[str] = []

    if search_query.strict:
        term_list = set([term.lower() for term in search_query.query_str.split()])
        logger.debug(
            f'"{search_query.query_str}" - strict mode enabled, title or asin must contain: {term_list}'
        )

    results_count = len(results_dict)

    generated_items = []

    for result in results_dict.values():
        item_id: str = result.get("asin")
        item_soup = BeautifulSoup(result.get("html"), features="html.parser")

        # select product title, use wildcard CSS selector for better international compatibility
        item_title_soup = item_soup.select_one("[class*='s-line-clamp-']")
        item_title = item_title_soup.text.strip() if item_title_soup else ""

        item_price_soup = item_soup.select_one(".a-price .a-offscreen")
        item_price = item_price_soup.text.strip() if item_price_soup else None
        item_price_text = item_price if item_price else "N/A"

        # reformat discounted price
        if item_price_soup and item_price_soup.select_one("span.price-large"):
            price_strings = list(item_price_soup.stripped_strings)
            item_price_text = (
                price_strings[0] + price_strings[1] + "." + price_strings[2]
            )

        item_thumbnail_soup = item_soup.find(
            attrs={"data-component-type": "s-product-image"}
        )
        item_thumbnail_img_soup = item_thumbnail_soup.select_one(".s-image")
        item_thumbnail_url = (
            item_thumbnail_img_soup.get("src") if item_thumbnail_img_soup else None
        )

        if item_price_soup:
            # search term must exist in item title or ASIN
            if search_query.strict and (
                term_list
                and not (
                    all(item_title.lower().find(term) >= 0 for term in term_list)
                    or item_id == search_query.query_str
                )
            ):
                logger.debug(
                    f'"{search_query.query_str}" - strict mode - removed {item_id} "{item_title}"'
                )
            else:
                feed_item = generate_item(
                    base_url, item_id, item_title, item_price_text, item_thumbnail_url
                )
                generated_items.append(feed_item)

    logger.info(
        f'"{search_query.query_str}" - found {results_count} - published {len(generated_items)}'
    )

    json_feed = get_top_level_feed(base_url, search_query, generated_items)

    return json_feed


def get_dimension_url(query: AmazonAsinQuery, item_id: str):
    #   Call the "dimension" endpoint which is used on mobile pages
    #   to display price and optionally availability for product variants

    locale_data = query.locale
    base_url = "https://" + locale_data.domain
    dimension_endpoint = base_url + "/gp/product/ajax?"

    query_dict = {
        "asinList": item_id,
        "experienceId": "twisterDimensionSlotsDefault",
        "asin": item_id,
        "deviceType": "mobile",
    }

    return dimension_endpoint + urlencode(query_dict)


def get_item_listing(query: AmazonAsinQuery):
    logger = query.config.logger

    item_id = query.query_str
    base_url = "https://" + query.locale.domain
    item_dimension_url = get_dimension_url(query, item_id)

    json_dict = get_response_dict(item_dimension_url, query)

    item_price_str: str = ""

    json_feed = get_top_level_feed(base_url, query, [])

    if json_dict:
        # Assume one item is returned per response
        result = (
            json_dict.get("Value", {}).get("content", {}).get("twisterSlotJson", {})
        )
        item_price_str = result.get("price")
    else:
        logger.error(query.query_str + " - no JSON response")
        return json_feed

    if not item_price_str:
        logger.error(query.query_str + " - price not found")
        return json_feed

    item_price_flt = "{0:.2f}".format(float(item_price_str))

    # exit if exceeded max price
    if item_price_str and query.max_price:

        # handle currencies without decimal places
        max_price_clean = (
            query.max_price + "00" if "." in item_price_str else query.max_price
        )

        if item_price_flt > float(max_price_clean):
            logger.info(f"{query.query_str} - exceeded max price {query.max_price}")
            return json_feed

    formatted_price = query.locale.currency + item_price_flt

    feed_item = generate_item(base_url, item_id, "", formatted_price, "")

    json_feed = get_top_level_feed(base_url, query, [feed_item])

    return json_feed
