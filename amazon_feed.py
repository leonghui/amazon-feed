from datetime import datetime
from amazon_feed_data import AmazonSearchQuery, AmazonListQuery
from json_feed_data import JsonFeedTopLevel, JsonFeedItem
from urllib.parse import quote_plus, urlparse, urlencode
from flask import abort
from requests import Session
from requests.utils import cookiejar_from_dict, dict_from_cookiejar
from dataclasses import asdict

import bleach
import random
from bs4 import BeautifulSoup


ITEM_QUANTITY = 1

country_to_domain = {
    'AU': 'www.amazon.com.au',
    'BR': 'www.amazon.com.br',
    'CA': 'www.amazon.ca',
    'CN': 'www.amazon.cn',
    'FR': 'www.amazon.fr',
    'DE': 'www.amazon.de',
    'IN': 'www.amazon.in',
    'IT': 'www.amazon.it',
    'JP': 'www.amazon.co.jp',
    'MX': 'www.amazon.com.mx',
    'NL': 'www.amazon.nl',
    'ES': 'www.amazon.es',
    'TR': 'www.amazon.com.tr',
    'AE': 'www.amazon.ae',
    'SG': 'www.amazon.sg',
    'UK': 'www.amazon.co.uk',
    'US': 'www.amazon.com'
}

allowed_tags = bleach.ALLOWED_TAGS + ['img', 'p']
allowed_attributes = bleach.ALLOWED_ATTRIBUTES.copy()
allowed_attributes.update({'img': ['src']})

session = Session()
user_agent = None

# mimic headers from Firefox 84.0
session.headers.update(
    {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'TE': 'Trailers'
    }
)


def get_domain(country, logger):
    domain = country_to_domain.get(country)

    if not domain:
        logger.info(f'Undefined country "{country}", defaulting to US')

    return domain if domain else country_to_domain.get('US')


def get_response_soup(url, query_object, useragent_list, logger):
    global user_agent

    domain = get_domain(query_object.country, logger)
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
        logger.debug('Error from source, dumping input:')
        logger.debug(response.text)
        abort(
            500, description=f"HTTP status from source: {response.status_code}")

    response_soup = BeautifulSoup(response.text, features='html.parser')

    if response_soup.find(id='captchacharacters'):
        user_agent = None
        logger.warning(f'{query_object.query} - Captcha triggered')
        abort(429, description='Captcha triggered')

    return response_soup


def get_search_url(base_url, query_object):
    search_uri = f"{base_url}/s?"

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
        if query_object.buybox_only:
            filters.append('buybox only')

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
    base_url = 'https://' + get_domain(search_query.country, logger)

    search_url = get_search_url(base_url, search_query)

    response_soup = get_response_soup(
        search_url, search_query, useragent_list, logger)

    # select search results with "s-result-item" and "s-asin" class attributes
    results_soup = response_soup.select('.s-result-item.s-asin')

    if search_query.strict:
        term_list = set([term.lower() for term in search_query.query.split()])
        logger.debug(
            f'"{search_query.query}" - strict mode enabled, title must contain: {term_list}')

    results_count = len(results_soup)

    json_feed = get_top_level_feed(base_url, search_query)

    for item_soup in results_soup:
        item_id = item_soup['data-asin']

        # select product title, use wildcard CSS selector for better international compatibility
        item_title_soup = item_soup.select_one("[class*='s-line-clamp-']")
        item_title = item_title_soup.text.strip() if item_title_soup else ''

        item_price_soup = item_soup.select_one('.a-price .a-offscreen')

        item_thumbnail_soup = item_soup.find(
            attrs={'data-component-type': 's-product-image'})
        item_thumbnail_img_soup = item_thumbnail_soup.select_one('.s-image')
        item_thumbnail_url = item_thumbnail_img_soup.get(
            'src') if item_thumbnail_img_soup else None

        if search_query.buybox_only and not item_price_soup:
            logger.debug(
                f'"{search_query.query}" - buybox only - removed {item_id} "{item_title}"')
        elif search_query.strict and (term_list and not all(item_title.lower().find(term) >= 0 for term in term_list)):
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
    base_url = 'https://' + get_domain(listing_query.country, logger)

    item_id = listing_query.query
    item_url = get_item_url(base_url, item_id)

    response_soup = get_response_soup(
        item_url, listing_query, useragent_list, logger)

    # select product title
    item_title_soup = response_soup.select_one('div#title_feature_div')

    # select price, use both desktop and mobile selectors
    item_price_soup = response_soup.select_one(
        'span.priceBlockDealPriceString,span#priceblock_dealprice,span#priceblock_ourprice')
    item_price = item_price_soup.text.strip() if item_price_soup else None

    # detect conditions where price is not found in the buybox
    # - out of stock
    # - unqualified buybox (supressed buy now price)
    # - partial buybox (size/type must be selected manually)
    missing_price_soup = response_soup.select_one(
        'div#outOfStock,div#unqualifiedBuyBox,div#partialStateBuybox')

    json_feed = get_top_level_feed(base_url, listing_query)

    if missing_price_soup:
        logger.info(
            f'"{listing_query.query}" - price not found in the buybox')
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
