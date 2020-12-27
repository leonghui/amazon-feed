from datetime import datetime
from amazon_feed_data import AmazonSearchQuery, AmazonListQuery
from json_feed_data import JsonFeedTopLevel, JsonFeedItem
from urllib.parse import quote_plus, urlparse, urlencode
from flask import abort

import bleach
import requests
import random
from bs4 import BeautifulSoup


JSONFEED_VERSION_URL = 'https://jsonfeed.org/version/1.1'
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


def get_domain(country):
    domain = country_to_domain.get(country)
    return domain if domain else country_to_domain.get('US')


def get_random_user_agent():

    # from https://github.com/Kikobeats/top-user-agents/blob/master/index.json
    user_agent_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:82.0) Gecko/20100101 Firefox/82.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:82.0) Gecko/20100101 Firefox/82.0",
        "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:82.0) Gecko/20100101 Firefox/82.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.193 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:82.0) Gecko/20100101 Firefox/82.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:83.0) Gecko/20100101 Firefox/83.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"
    ]

    return random.choice(user_agent_list)


def get_response_soup(url, query_object, logger):

    session = requests.Session()
    user_agent = get_random_user_agent()
    logger.debug(f'"{query_object.query}" - Using user-agent: "{user_agent}"')

    # mimic headers from Firefox 84.0
    session.headers.update(
        {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.amazon.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'TE': 'Trailers'
        }
    )

    logger.debug(f'"{query_object.query}" - Querying endpoint: {url}')
    response = session.get(url)

    # return HTTP error code
    if not response.ok:
        abort(
            500, description=f"HTTP status from source: {response.status_code}")

    response_soup = BeautifulSoup(response.text, features='html.parser')

    if response_soup.find(id='captchacharacters'):
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
        version=JSONFEED_VERSION_URL,
        title=' - '.join(title_strings),
        home_page_url=home_page_url,
        favicon=base_url + '/favicon.ico'
    )

    return json_feed


def generate_item(base_url, item_id, item_title_soup, item_price_soup, item_thumbnail_url):
    item_title = item_title_soup.text.strip() if item_title_soup else ''

    item_price = item_price_soup.text.strip() if item_price_soup else None
    item_price_text = item_price if item_price else 'N/A'

    item_thumbnail_html = f'<img src=\"{item_thumbnail_url}\" /><p>'

    item_add_to_cart_url = f"{base_url}/gp/aws/cart/add.html?ASIN.1={item_id}&Quantity.1={ITEM_QUANTITY}"
    item_add_to_cart_html = f'<a href=\"{item_add_to_cart_url}\">Add to Cart</a></p>'

    content_body = item_thumbnail_html + \
        item_add_to_cart_html if item_thumbnail_url else item_thumbnail_html

    sanitized_html = bleach.clean(
        content_body,
        tags=allowed_tags,
        attributes=allowed_attributes
    ).replace('&amp;', '&')  # restore raw ampersands: https://github.com/mozilla/bleach/issues/192

    timestamp = datetime.now().timestamp()

    feed_item = JsonFeedItem(
        id=datetime.utcfromtimestamp(timestamp).isoformat('T'),
        url=get_item_url(base_url, item_id),
        title=f"[{item_price_text}] {item_title}",
        content_html=sanitized_html,
        image=item_thumbnail_url,
        date_published=datetime.utcfromtimestamp(timestamp).isoformat('T')
    )

    return feed_item


def get_search_results(search_query, logger):
    base_url = f"https://{get_domain(search_query.country)}"

    search_url = get_search_url(base_url, search_query)

    response_soup = get_response_soup(search_url, search_query, logger)

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

        # select product title, use wildcard CSS selector for better compatibility
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


def get_item_listing(listing_query, logger):
    base_url = 'https://' + get_domain(listing_query.country)

    item_id = listing_query.query
    item_url = get_item_url(base_url, item_id)

    response_soup = get_response_soup(item_url, listing_query, logger)

    # select product title
    item_title_soup = response_soup.select_one('span#productTitle')

    # select price in the buybox
    item_price_soup = response_soup.select_one('span#price_inside_buybox')
    oos_soup = response_soup.select_one('div#outOfStock')
    unqualified_buybox_soup = response_soup.select_one('div#unqualifiedBuyBox')

    json_feed = get_top_level_feed(base_url, listing_query)

    # exit if unqualified buybox or out of stock
    if unqualified_buybox_soup or oos_soup:
        logger.info(
            f'"{listing_query.query}" - unqualified buybox or out of stock')
        return json_feed

    item_thumbnail_soup = response_soup.select_one('div#main-image-container')
    item_thumbnail_img_soup = item_thumbnail_soup.select_one(
        'img#landingImage')
    item_thumbnail_url = item_thumbnail_img_soup.get(
        'data-old-hires') if item_thumbnail_img_soup else None

    feed_item = generate_item(
        base_url, item_id, item_title_soup, item_price_soup, item_thumbnail_url)

    json_feed.items.append(feed_item)

    return json_feed
