from datetime import datetime
from amazon_feed_data import AmazonSearchQuery, AmazonListQuery
from json_feed_data import JsonFeedTopLevel, JsonFeedItem, JSONFEED_VERSION_URL
from urllib.parse import quote_plus, urlparse, urlencode
from flask import abort
from requests.exceptions import JSONDecodeError, RequestException
from requests_cache import CachedSession

import bleach
import random
import json
import time
from bs4 import BeautifulSoup


ITEM_QUANTITY = 1
RETRY_COUNT = 3
RETRY_WAIT_SEC = 5
CACHE_EXPIRATION_SEC = 60

allowed_tags = bleach.ALLOWED_TAGS + ['img', 'p']
allowed_attributes = bleach.ALLOWED_ATTRIBUTES.copy()
allowed_attributes.update({'img': ['src']})
STREAM_DELIMITER = '&&&'    # application/json-amazonui-streaming

session = CachedSession(
    allowable_methods=('GET', 'POST'),
    stale_if_error=True,
    expire_after=CACHE_EXPIRATION_SEC,
    backend='memory')
user_agent = None

# mimic headers from Firefox 84.0
headers = {
        'Accept': 'text/html,*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'TE': 'Trailers'
    }


def get_response_dict(url, query_object, useragent_list, logger):
    global user_agent

    referer = 'https://' + query_object.locale.domain + '/'
    headers['Referer'] = referer

    if useragent_list and not user_agent:
        user_agent = random.choice(useragent_list)
        logger.debug(
            f'"{query_object.query}" - using user-agent: "{user_agent}"')

    if user_agent:
        headers['User-Agent'] = user_agent

    logger.debug(f'"{query_object.query}" - querying endpoint: {url}')

    try:
        response = session.post(url, headers=headers)
    except RequestException as ex:
        logger.error(f'"{query_object.query}" - {type(ex)}: {ex}')
        logger.debug(
            f'"{query_object.query}" - dumping input: {response.text}')
        abort(500, description=ex)

    # return HTTP error code
    if not response.ok:
        user_agent = None
        if response.status_code == 503:
            logger.warning(query_object.query + ' - API paywall triggered')
            abort(503, description='API paywall triggered')
        else:
            logger.error(f'"{query_object.query}" - error from source')
            logger.debug(
                f'"{query_object.query}" - dumping input: {response.text}')
            abort(
                500, description=f"HTTP status from source: {response.status_code}")
    else:
        logger.debug(
            f'"{query_object.query}" - response cached: {response.from_cache}')

    # Each "application/json-amazonui-streaming" payload is a triple:
    # ["dispatch",
    #  "data-main-slot:search-result-2",
    #  {
    #      "html": ...,
    #      "asin": "B00TSUGXKE",
    #      "index": 2
    #  }]

    # split streamed payload and store as a list
    if STREAM_DELIMITER in response.text:

        json_list_str = response.text.split(STREAM_DELIMITER)

        # remove last triple if empty
        if len(json_list_str[-1]) == 1:
            del json_list_str[-1]

        # decode each payload and store as a nested list
        json_nested_list = [json.loads(_str) for _str in json_list_str]

        # convert payload to dict using 2nd and 3rd elements as key-value pairs
        json_dict = {_list[1]: _list[2] for _list in json_nested_list}

        return json_dict
    else:
        try:
            return response.json()
        except JSONDecodeError as jdex:
            if response.text.find("captcha"):
                logger.warning(query_object.query + ' - API paywall triggered')
                abort(503, description='API paywall triggered')
            else:
                logger.error(f'"{query_object.query}" - {type(jdex)}: {jdex}')
                logger.debug(
                    f'"{query_object.query}" - dumping input: {response.text}')
            return None


def get_search_url(base_url, query_object, is_xhr=False):
    search_uri = f"{base_url}/s/query?" if is_xhr else f"{base_url}/s?"

    search_dict = {'k': quote_plus(query_object.query)}

    price_param_value = min_price = max_price = None

    if query_object.min_price or query_object.max_price:
        price_param = 'p_36:'
        if query_object.min_price:
            min_price = query_object.min_price + '00'
        if query_object.max_price:
            max_price = query_object.max_price + '00'

        price_param_value = ''.join(
            item for item in [price_param, min_price, '-', max_price] if item)

    if price_param_value:
        search_dict['rh'] = price_param_value

    return search_uri + urlencode(search_dict)


def get_item_url(base_url, item_id):
    return base_url + '/gp/product/' + item_id


def get_top_level_feed(base_url, query_object, feed_items):

    parse_object = urlparse(base_url)
    domain = parse_object.netloc

    title_strings = [domain, query_object.query]

    filters = []

    if isinstance(query_object, AmazonSearchQuery):
        home_page_url = get_search_url(base_url, query_object)

        if query_object.strict:
            filters.append('strict')

    elif isinstance(query_object, AmazonListQuery):
        home_page_url = get_item_url(base_url, query_object.query)

    if query_object.min_price:
        filters.append(f"min {query_object.min_price}")

    if query_object.max_price:
        filters.append(f"max {query_object.max_price}")

    if filters:
        title_strings.append(f"filtered by {', '.join(filters)}")

    json_feed = JsonFeedTopLevel(
        version=JSONFEED_VERSION_URL,
        items=feed_items,
        title=' - '.join(title_strings),
        home_page_url=home_page_url,
        favicon=base_url + '/favicon.ico'
    )

    return json_feed


def generate_item(base_url, item_id, item_title, item_price_text, item_thumbnail_url):
    item_title_text = item_title.strip() if item_title else item_id

    item_thumbnail_html = f'<img src=\"{item_thumbnail_url}\" />'

    timestamp = datetime.now().timestamp()
    timestamp_html = f"<p>Last updated: {datetime.fromtimestamp(timestamp).strftime('%d %B %Y %I:%M%p')}</p>"

    item_link_url = get_item_url(base_url, item_id)
    item_link_html = f'<p><a href=\"{item_link_url}\">Product Link</a></p>'

    item_add_to_cart_url = f"{base_url}/gp/aws/cart/add.html?ASIN.1={item_id}&Quantity.1={ITEM_QUANTITY}"
    item_add_to_cart_html = f'<p><a href=\"{item_add_to_cart_url}\">Add to Cart</a></p>'

    content_body_list = [timestamp_html, item_link_html, item_add_to_cart_html]

    if item_thumbnail_url:
        content_body_list.insert(0, item_thumbnail_html)

    content_body = ''.join(content_body_list)

    sanitized_html = bleach.clean(
        content_body,
        tags=allowed_tags,
        attributes=allowed_attributes
    ).replace('&amp;', '&')  # restore raw ampersands: https://github.com/mozilla/bleach/issues/192

    feed_item = JsonFeedItem(
        id=datetime.utcfromtimestamp(timestamp).isoformat('T'),
        url=item_link_url,
        title=f"[{item_price_text}] {item_title_text}",
        content_html=sanitized_html,
        image=item_thumbnail_url,
        date_published=datetime.utcfromtimestamp(timestamp).isoformat('T')
    )

    return feed_item


def get_search_results(search_query, useragent_list, logger):
    base_url = 'https://' + search_query.locale.domain

    search_url = get_search_url(base_url, search_query, is_xhr=True)

    json_dict = get_response_dict(
        search_url, search_query, useragent_list, logger)

    results_dict = {k: v for k, v in json_dict.items() if k.startswith(
        'data-main-slot:search-result-')}

    if search_query.strict:
        term_list = set([term.lower() for term in search_query.query.split()])
        logger.debug(
            f'"{search_query.query}" - strict mode enabled, title must contain: {term_list}')

    results_count = json_dict.get(
        'data-search-metadata').get('metadata').get('totalResultCount')

    generated_items = []

    for result in results_dict.values():
        item_id = result.get('asin')
        item_soup = BeautifulSoup(result.get('html'), features='html.parser')

        # select product title, use wildcard CSS selector for better international compatibility
        item_title_soup = item_soup.select_one("[class*='s-line-clamp-']")
        item_title = item_title_soup.text.strip() if item_title_soup else ''

        item_price_soup = item_soup.select_one('.a-price .a-offscreen')
        item_price = item_price_soup.text.strip() if item_price_soup else None
        item_price_text = item_price if item_price else 'N/A'

        # reformat discounted price
        if item_price_soup and item_price_soup.select_one('span.price-large'):
            price_strings = list(item_price_soup.stripped_strings)
            item_price_text = price_strings[0] + \
                price_strings[1] + '.' + price_strings[2]

        item_thumbnail_soup = item_soup.find(
            attrs={'data-component-type': 's-product-image'})
        item_thumbnail_img_soup = item_thumbnail_soup.select_one('.s-image')
        item_thumbnail_url = item_thumbnail_img_soup.get(
            'src') if item_thumbnail_img_soup else None

        if item_price_soup:
            if search_query.strict and (term_list and not all(item_title.lower().find(term) >= 0 for term in term_list)):
                logger.debug(
                    f'"{search_query.query}" - strict mode - removed {item_id} "{item_title}"')
            else:
                feed_item = generate_item(
                    base_url, item_id, item_title, item_price_text, item_thumbnail_url)
                generated_items.append(feed_item)

    logger.info(
        f'"{search_query.query}" - found {results_count} - published {len(generated_items)}')

    json_feed = get_top_level_feed(base_url, search_query, generated_items)

    return json_feed


def get_dimension_url(listing_query, logger, item_id):
    #   Call the dimension endpoint which is used on mobile pages to display price and availability for product variants
    #   Use a pair of ASINs with a valid parent-child relationship to trigger a response

    locale_data = listing_query.locale
    base_url = 'https://' + locale_data.domain
    dimension_endpoint = base_url + '/gp/twister/dimension?'

    query_dict = {
        'asinList': locale_data.child_asin + ',' + item_id,
        'productTypeDefinition': None,
        'productGroupId': locale_data.product_group,
        'parentAsin': locale_data.parent_asin
    }

    return dimension_endpoint + urlencode(query_dict)


def get_item_listing(listing_query, useragent_list, logger):
    item_id = listing_query.query
    base_url = 'https://' + listing_query.locale.domain
    item_dimension_url = get_dimension_url(listing_query, logger, item_id)

    for x in range(RETRY_COUNT):
        json_dict = get_response_dict(
            item_dimension_url, listing_query, useragent_list, logger)
        if not json_dict:
            session.cache.clear() # treat empty response as stale
            logger.warning(
                f'"{listing_query.query}" - retrying {x + 1} time(s)')
            time.sleep(RETRY_WAIT_SEC)
        else:
            break

    if json_dict:
        matching_result = next(
            result for result in json_dict if result['asin'] == item_id)
        item_price = matching_result['price'] \
            if matching_result['price'] else matching_result['availability']
    else:
        item_price = None

    json_feed = get_top_level_feed(base_url, listing_query, [])

    if not item_price:
        logger.info(listing_query.query + ' - price not found')
        return json_feed

    # exit if exceeded max price
    if item_price and listing_query.max_price:
        item_price_clean = ''.join(filter(str.isnumeric, item_price))

        # handle currencies without decimal places
        max_price_clean = listing_query.max_price + \
            '00' if '.' in item_price else listing_query.max_price

        if float(item_price_clean) > float(max_price_clean):
            logger.info(
                f'"{listing_query.query}" - exceeded max price {listing_query.max_price}')
            return json_feed

    feed_item = generate_item(base_url, item_id, None, item_price, None)

    json_feed = get_top_level_feed(base_url, listing_query, [feed_item])

    return json_feed
