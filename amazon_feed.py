from datetime import datetime
from logging import Logger
import re
from urllib.parse import ParseResult, quote_plus, urlencode, urlparse

from bs4 import BeautifulSoup
from bs4._typing import _AtMostOneTag, _AttributeValue
from bs4.element import ResultSet, Tag
from flask import abort
import nh3
from requests.exceptions import JSONDecodeError, RequestException
from requests_cache.models import AnyResponse
from requests_cache.session import CachedSession

from amazon_feed_data import (
    AmazonAsinQuery,
    AmazonKeywordQuery,
    AmazonLocale,
    BOT_PATTERN,
    FilterableQuery,
)
from json_feed_data import JSONFEED_VERSION_URL, JsonFeedItem, JsonFeedTopLevel

ITEM_QUANTITY = 1

allowed_tags: set[str] = {"a", "img", "p"}
allowed_attributes: dict[str, set[str]] = {"a": {"href", "title"}, "img": {"src"}}
STREAM_DELIMITER = "&&&"  # application/json-amazonui-streaming

# mimic headers from Android app
headers: dict[str, str] = {
    "Accept": "text/html,*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "device-memory": "8",
    "downlink": "9.3",
    "dpr": "2",
    "ect": "4g",
    "rtt": "0",
    "sec-ch-device-memory": "8",
    "sec-ch-dpr": "2",
    "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Android WebView";v="128"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua-platform-version": '""',
    "sec-ch-viewport-width": "393",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "viewport-width": "393",
}


def clear_session_cookies(query: FilterableQuery) -> None:
    query.config.session.cookies.clear()


def handle_response(response: AnyResponse, query: FilterableQuery):
    logger: Logger = query.config.logger

    try:
        return response.json()
    except JSONDecodeError as jdex:
        logger.debug(msg=f"{query.query_str} - {type(jdex)}: {jdex}")
        logger.debug(msg=f"{query.query_str} - dumping response: {response.text}")
        return None


def get_response(url: str, query: FilterableQuery) -> AnyResponse:
    logger: Logger = query.config.logger
    session: CachedSession = query.config.session

    headers["User-Agent"] = query.config.useragent
    headers["Referer"] = "https://" + query.locale.domain + "/"

    logger.debug(msg=f"{query.query_str} - querying endpoint: {url}")

    try:
        response: AnyResponse = session.get(url, headers=headers)
    except RequestException as rex:
        clear_session_cookies(query)
        logger.error(msg=f"{query.query_str} - {type(rex)}: {rex}")
        abort(code=500)

    # return HTTP error code
    if not response.ok:
        if response.status_code == 503 or re.search(BOT_PATTERN, response.text):
            bot_msg: str = (
                f"{query.query_str} - API paywall triggered, resetting session"
            )
            clear_session_cookies(query)

            logger.warning(msg=bot_msg)
            abort(code=429, description=bot_msg)
        else:
            logger.error(msg=f"{query.query_str} - error from source")
            logger.debug(msg=f"{query.query_str} - dumping response: {response.text}")
            abort(code=500)
    else:
        logger.debug(msg=f"{query.query_str} - response cached: {response.from_cache}")

    return response


def get_response_dict(url: str, query: FilterableQuery):
    response: AnyResponse = get_response(url, query)
    return handle_response(response, query)


def get_search_url(base_url: str, query: FilterableQuery):
    search_uri: str = f"{base_url}/s?"

    search_dict: dict[str, str] = {"k": quote_plus(string=query.query_str)}

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

    return search_uri + urlencode(query=search_dict)


def get_item_url(base_url: str, item_id: str) -> str:
    return base_url + "/gp/product/" + item_id


def get_top_level_feed(
    base_url: str, query: FilterableQuery, feed_items: list[JsonFeedItem]
) -> JsonFeedTopLevel:
    parse_object: ParseResult = urlparse(url=base_url)
    domain: str = parse_object.netloc

    title_strings: list[str] = [domain, query.query_str]

    filters = []

    if isinstance(query, AmazonKeywordQuery):
        home_page_url: str = get_search_url(base_url, query)

        if query.strict:
            filters.append("strict")

    elif isinstance(query, AmazonAsinQuery):
        home_page_url = get_item_url(base_url, item_id=query.query_str)

    if query.min_price:
        filters.append(f"min {query.locale.currency}{query.min_price}")

    if query.max_price:
        filters.append(f"max {query.locale.currency}{query.max_price}")

    if filters:
        title_strings.append(f"filtered by {', '.join(filters)}")

    json_feed: JsonFeedTopLevel = JsonFeedTopLevel(
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
) -> JsonFeedItem:
    item_title_text: str = item_title.strip() if item_title else item_id

    item_thumbnail_html: str = f'<img src="{item_thumbnail_url}" />'

    timestamp: float = datetime.now().timestamp()

    item_link_url: str = get_item_url(base_url, item_id)
    item_link_html: str = f'<p><a href="{item_link_url}">Product Link</a></p>'

    item_add_to_cart_url: str = (
        f"{base_url}/gp/aws/cart/add.html?ASIN.1={item_id}&Quantity.1={ITEM_QUANTITY}"
    )
    item_add_to_cart_html: str = (
        f'<p><a href="{item_add_to_cart_url}">Add to Cart</a></p>'
    )

    content_body_list: list[str] = [item_link_html, item_add_to_cart_html]

    if item_thumbnail_url:
        content_body_list.insert(0, item_thumbnail_html)

    content_body: str = "".join(content_body_list)

    sanitized_html: str = nh3.clean(
        html=content_body, tags=allowed_tags, attributes=allowed_attributes
    ).replace(
        "&amp;", "&"
    )  # restore raw ampersands: https://github.com/mozilla/bleach/issues/192

    feed_item: JsonFeedItem = JsonFeedItem(
        id=datetime.utcfromtimestamp(timestamp).isoformat("T"),
        url=item_link_url,
        title=f"[{item_price_text}] {item_title_text}",
        content_html=sanitized_html,
        image=item_thumbnail_url,
        date_published=datetime.utcfromtimestamp(timestamp).isoformat("T"),
    )

    return feed_item


def get_keyword_results(search_query: AmazonKeywordQuery) -> JsonFeedTopLevel:
    logger: Logger = search_query.config.logger

    base_url: str = "https://" + search_query.locale.domain

    search_url: str = get_search_url(base_url, query=search_query)

    response: AnyResponse = get_response(url=search_url, query=search_query)

    response_soup: BeautifulSoup = BeautifulSoup(
        markup=response.content, features="html.parser"
    )

    results: ResultSet[Tag] = response_soup.select(
        selector="div.s-asin.s-result-item:not(.AdHolder)"
    )

    results_dict: dict[_AttributeValue, Tag] = {
        div["data-asin"]: div for div in results
    }

    term_list: list[str] = []

    if search_query.strict:
        term_list: list[str] = set(
            [term.lower() for term in search_query.query_str.split()]
        )
        logger.debug(
            msg=f'"{search_query.query_str}" - strict mode enabled, title or asin must contain: {term_list}'
        )

    results_count: int = len(results_dict)

    generated_items = []

    for item_id, item_soup in results_dict.items():
        # select product title, use wildcard CSS selector for better international compatibility
        item_title_soup = item_soup.select_one("h2.s-line-clamp-3")
        item_title = item_title_soup["aria-label"].strip() if item_title_soup else ""

        item_voucher_soup = item_soup.select_one("span.s-coupon-unclipped")
        item_voucher = item_voucher_soup.text.strip() if item_voucher_soup else None
        item_title_text = (
            f"({item_voucher}) {item_title}" if item_voucher else item_title
        )

        item_price_soup = item_soup.select_one(".a-price .a-offscreen")
        item_price = item_price_soup.text.strip() if item_price_soup else None
        item_price_text = item_price if item_price else "N/A"

        # reformat discounted price
        if item_price_soup and item_price_soup.select_one("span.price-large"):
            price_strings = list(item_price_soup.stripped_strings)
            item_price_text = (
                price_strings[0] + price_strings[1] + "." + price_strings[2]
            )

        item_thumbnail_soup: _AtMostOneTag = item_soup.find(
            attrs={"data-component-type": "s-product-image"}
        )
        item_thumbnail_img_soup: Tag | None = item_thumbnail_soup.select_one(
            selector=".s-image"
        )
        item_thumbnail_url: _AttributeValue | None = (
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
                    msg=f'"{search_query.query_str}" - strict mode - removed {item_id} "{item_title}"'
                )
            else:
                feed_item: JsonFeedItem = generate_item(
                    base_url,
                    item_id,
                    item_title_text,
                    item_price_text,
                    item_thumbnail_url,
                )
                generated_items.append(feed_item)

    logger.info(
        msg=f'"{search_query.query_str}" - found {results_count} - published {len(generated_items)}'
    )

    json_feed: JsonFeedTopLevel = get_top_level_feed(
        base_url, query=search_query, feed_items=generated_items
    )

    return json_feed


def get_dimension_url(query: AmazonAsinQuery, item_id: str) -> str:
    #   Call the "dimension" endpoint which is used on mobile pages
    #   to display price and optionally availability for product variants

    locale_data: AmazonLocale = query.locale
    base_url: str = "https://" + locale_data.domain
    dimension_endpoint: str = base_url + "/gp/product/ajax?"

    query_dict: dict[str, str] = {
        "asinList": item_id,
        "experienceId": "twisterDimensionSlotsDefault",
        "asin": item_id,
        "deviceType": "mobile",
    }

    return dimension_endpoint + urlencode(query=query_dict)


def get_item_listing(query: AmazonAsinQuery) -> JsonFeedTopLevel:
    logger: Logger = query.config.logger

    item_id: str = query.query_str
    base_url: str = "https://" + query.locale.domain
    item_dimension_url: str = get_dimension_url(query, item_id)

    json_dict = get_response_dict(url=item_dimension_url, query=query)

    item_price_str: str = ""

    json_feed: JsonFeedTopLevel = get_top_level_feed(base_url, query, feed_items=[])

    if json_dict:
        # Assume one item is returned per response
        result = (
            json_dict.get("Value", {}).get("content", {}).get("twisterSlotJson", {})
        )
        item_price_str = result.get("price")
    else:
        logger.error(msg=query.query_str + " - no JSON response")
        return json_feed

    if not item_price_str:
        logger.error(msg=query.query_str + " - price not found")
        return json_feed

    item_price: str = "{0:.2f}".format(float(item_price_str))

    # exit if exceeded max price
    if item_price_str and query.max_price:
        if float(item_price) > float(query.max_price):
            logger.info(msg=f"{query.query_str} - exceeded max price {query.max_price}")
            return json_feed

    formatted_price: str = query.locale.currency + item_price

    feed_item: JsonFeedItem = generate_item(
        base_url,
        item_id,
        item_title="",
        item_price_text=formatted_price,
        item_thumbnail_url="",
    )

    json_feed = get_top_level_feed(base_url, query, feed_items=[feed_item])

    return json_feed
