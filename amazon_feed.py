from datetime import datetime
from amazon_feed_data import AmazonSearchQuery, AmazonListQuery, get_amazon_domain
from json_feed_data import JsonFeedTopLevel, JsonFeedItem
from urllib.parse import quote_plus, urlparse, urlencode
from flask import abort
from requests import Session
from requests.utils import cookiejar_from_dict, dict_from_cookiejar
from dataclasses import asdict

import bleach
import random
import json
from bs4 import BeautifulSoup


ITEM_QUANTITY = 1

allowed_tags = bleach.ALLOWED_TAGS + ['img', 'p']
allowed_attributes = bleach.ALLOWED_ATTRIBUTES.copy()
allowed_attributes.update({'img': ['src']})
STREAM_DELIMITER = '&&&'    # application/json-amazonui-streaming

session = Session()
user_agent = None

# mimic headers from Firefox 84.0
session.headers.update(
    {
        'Accept': 'text/html,*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'TE': 'Trailers',
    }
)


def get_response_soup(url, query_object, useragent_list, logger):
    global user_agent

    domain = get_amazon_domain(query_object.country, logger)
    referer = 'https://' + domain + '/'
    headers = {'Referer': referer}

    if useragent_list and not user_agent:
        user_agent = random.choice(useragent_list)
        logger.debug(
            f'"{query_object.query}" - Using user-agent: "{user_agent}"')

    if user_agent:
        headers['User-Agent'] = user_agent

    logger.debug(f'"{query_object.query}" - Querying endpoint: {url}')

    try:
        response = session.get(url, headers=headers)
    except Exception as ex:
        logger.debug('Exception:' + ex)
        abort(500, description=ex)

    # return HTTP error code
    if not response.ok:
        user_agent = None
        logger.error(query_object.query + ' - error from source')
        logger.debug(query_object.query + ' - dumping input:' + response.text)
        abort(
            500, description='HTTP status from source: ' + str(response.status_code))

    response_soup = BeautifulSoup(response.text, features='html.parser')

    if response_soup.find(id='captchacharacters'):
        user_agent = None
        logger.warning(f'{query_object.query} - Captcha triggered')
        abort(429, description='Captcha triggered')

    return response_soup


def get_response_dict(url, query_object, useragent_list, logger):
    global user_agent

    domain = get_amazon_domain(query_object.country, logger)
    referer = 'https://' + domain + '/'
    headers = {'Referer': referer}

    if useragent_list and not user_agent:
        user_agent = random.choice(useragent_list)
        logger.debug(
            f'"{query_object.query}" - Using user-agent: "{user_agent}"')

    if user_agent:
        headers['User-Agent'] = user_agent

    logger.debug(f'"{query_object.query}" - Querying endpoint: {url}')

    try:
        response = session.post(url, headers=headers)
    except Exception as ex:
        logger.debug('Exception:' + ex)
        abort(500, description=ex)

    # return HTTP error code
    if not response.ok:
        user_agent = None
        if response.status_code == 503:
            logger.warning(query_object.query + ' - API paywall triggered')
            abort(503, description='API paywall triggered')
        else:
            logger.error(query_object.query + ' - error from source')
            logger.debug(query_object.query +
                         ' - dumping input:' + response.text)
            abort(
                500, description='HTTP status from source: ' + str(response.status_code))

    # Each "application/json-amazonui-streaming" payload is a triple:
    # ["dispatch",
    #  "data-main-slot:search-result-2",
    #  {
    #      "html": ...,
    #      "asin": "B00TSUGXKE",
    #      "index": 2
    #  }]

    # split streamed payload and store as a list
    json_list_str = response.text.split(STREAM_DELIMITER)

    # remove last triple if empty
    if len(json_list_str[-1]) == 1:
        del json_list_str[-1]

    # decode each payload and store as a nested list
    json_nested_list = [json.loads(_str) for _str in json_list_str]

    # convert payload to dict using 2nd and 3rd elements as key-value pairs
    json_dict = {_list[1]: _list[2] for _list in json_nested_list}

    return json_dict


def get_search_url(base_url, query_object):
    search_uri = f"{base_url}/s/query?"

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


def get_top_level_feed(base_url, query_object):

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
        items=[],
        title=' - '.join(title_strings),
        home_page_url=home_page_url,
        favicon=base_url + '/favicon.ico'
    )

    return json_feed


def generate_item(base_url, item_id, item_title_soup, item_price_soup, item_thumbnail_url):
    item_title = item_title_soup.text.strip() if item_title_soup else ''

    item_price = item_price_soup.text.strip() if item_price_soup else None
    item_price_text = item_price if item_price else 'N/A'

    # reformat discounted price
    if item_price_soup and item_price_soup.select_one('span.price-large'):
        price_strings = list(item_price_soup.stripped_strings)
        item_price_text = price_strings[0] + \
            price_strings[1] + '.' + price_strings[2]

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
        title=f"[{item_price_text}] {item_title}",
        content_html=sanitized_html,
        image=item_thumbnail_url,
        date_published=datetime.utcfromtimestamp(timestamp).isoformat('T')
    )

    return feed_item


def get_search_results(search_query, useragent_list, logger):
    base_url = 'https://' + get_amazon_domain(search_query.country, logger)

    search_url = get_search_url(base_url, search_query)

    json_dict = get_response_dict(
        search_url, search_query, useragent_list, logger)

    results_dict = {k: v for k, v in json_dict.items() if k.startswith(
        'data-main-slot:search-result-')}

    json_feed = get_top_level_feed(base_url, search_query)

    if search_query.strict:
        term_list = set([term.lower() for term in search_query.query.split()])
        logger.debug(
            f'"{search_query.query}" - strict mode enabled, title must contain: {term_list}')

    results_count = json_dict.get(
        'data-search-metadata').get('metadata').get('totalResultCount')

    for result in results_dict.values():
        item_id = result.get('asin')
        item_soup = BeautifulSoup(result.get('html'), features='html.parser')

        # select product title, use wildcard CSS selector for better international compatibility
        item_title_soup = item_soup.select_one("[class*='s-line-clamp-']")
        item_title = item_title_soup.text.strip() if item_title_soup else ''

        item_price_soup = item_soup.select_one('.a-price .a-offscreen')

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
                    base_url, item_id, item_title_soup, item_price_soup, item_thumbnail_url)
                json_feed.items.append(feed_item)

    logger.info(
        f'"{search_query.query}" - found {results_count} - published {len(json_feed.items)}')

    return json_feed


# modified from https://stackoverflow.com/a/24893252
def remove_empty_from_dict(d):
    if isinstance(d, dict):
        return dict((k, remove_empty_from_dict(v)) for k, v in d.items() if v and remove_empty_from_dict(v))
    elif isinstance(d, list):
        return [remove_empty_from_dict(v) for v in d if v and remove_empty_from_dict(v)]
    else:
        return d


def get_item_listing(listing_query, useragent_list, logger):
    base_url = 'https://' + get_amazon_domain(listing_query.country, logger)

    item_id = listing_query.query
    item_url = get_item_url(base_url, item_id)

    response_soup = get_response_soup(
        item_url, listing_query, useragent_list, logger)

    # select product title
    item_title_soup = response_soup.select_one('div#title_feature_div')

    # select price, use both desktop and mobile selectors
    item_price_soup = response_soup.select_one('''
        div#newPitchPriceWrapper_feature_div,
        span.priceBlockDealPriceString,
        span#priceblock_dealprice,
        span#priceblock_ourprice
    ''')

    item_price = item_price_soup.text.strip() if item_price_soup else None

    json_feed = get_top_level_feed(base_url, listing_query)

    if not(item_price):
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
                f'"{listing_query.query}" - exceeded max price {max_price_clean}')
            return json_feed

    item_thumbnail_url = None

    item_thumbnail_img_soup = response_soup.select_one(
        'div#main-image-container img#landingImage,div#landing-image-wrapper img#main-image')

    # prefer "src" least because it contains image embedded as data uri when queried without JS
    if item_thumbnail_img_soup:
        item_thumbnail_url_list = [item_thumbnail_img_soup.get(attr) for attr in [
            'data-a-hires', 'data-old-hires', 'src'] if item_thumbnail_img_soup.has_attr(attr)]
        item_thumbnail_url = item_thumbnail_url_list[0]
    else:
        logger.info(f'"{listing_query.query}" - thumbnail not found')

    feed_item = generate_item(
        base_url, item_id, item_title_soup, item_price_soup, item_thumbnail_url)

    json_feed.items.append(feed_item)

    return remove_empty_from_dict(asdict(json_feed))
