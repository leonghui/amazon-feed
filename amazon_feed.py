from datetime import datetime
from amazon_search_query_class import AmazonSearchQueryClass
from urllib.parse import quote_plus, urlparse, urlencode

import bleach
import logging
import requests
import random
from bs4 import BeautifulSoup


JSONFEED_VERSION_URL = 'https://jsonfeed.org/version/1'

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

logging.basicConfig(level=logging.INFO)

allowed_tags = bleach.ALLOWED_TAGS + ['br', 'img', 'span', 'u', 'p']
allowed_attributes = bleach.ALLOWED_ATTRIBUTES.copy()
allowed_attributes.update({'img': ['src']})
allowed_attributes.update({'span': ['style']})
allowed_styles = ['color']


def get_domain(country):
    domain = country_to_domain.get(country)
    return domain if domain else country_to_domain.get('US')


def handle_response(response):

    # return HTTP error code
    if not response.ok:
        msg = f"HTTP error {response.status_code}"
        logging.error(msg)
        return msg

    return response


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


def get_search_response(url):
    logging.debug(f"Querying endpoint: {url}")

    session = requests.Session()
    user_agent = get_random_user_agent()
    logging.debug(f"Using user-agent: {user_agent}")

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

    response = session.get(url)

    return handle_response(response)


def get_search_url(base_url, search_query):
    search_uri = f"{base_url}/s?"

    search_dict = {'k': quote_plus(search_query.query)}

    price_param_value = min_price = max_price = None

    if search_query.min_price or search_query.max_price:
        price_param = 'p_36:'
        if search_query.min_price:
            min_price = search_query.min_price + '00'
        if search_query.max_price:
            max_price = search_query.max_price + '00'

        price_param_value = ''.join(
            item for item in [price_param, min_price, '-', max_price] if item)

    if price_param_value:
        search_dict['rh'] = price_param_value

    return search_uri + urlencode(search_dict)


def get_top_level_feed(base_url, search_query):

    parse_object = urlparse(base_url)
    domain = parse_object.netloc

    title_strings = [domain, search_query.query]

    filters = []

    if search_query.min_price:
        filters.append(f"min {search_query.min_price}")

    if search_query.max_price:
        filters.append(f"max {search_query.max_price}")

    if search_query.srp_only:
        filters.append('srp only')

    if search_query.strict:
        filters.append('strict')

    if filters:
        title_strings.append(f"filtered by {', '.join(filters)}")

    output = {
        'version': JSONFEED_VERSION_URL,
        'title': ' - '.join(title_strings),
        'home_page_url': get_search_url(base_url, search_query),
        'favicon': base_url + '/favicon.ico'
    }

    return output


def get_listing(search_query):
    base_url = f"https://{get_domain(search_query.country)}"

    search_url = get_search_url(base_url, search_query)

    response_body = get_search_response(search_url)

    response_soup = BeautifulSoup(response_body.text, features='html.parser')

    # select search results with "s-result-item" and "s-asin" class attributes
    results_soup = response_soup.select('.s-result-item.s-asin')

    if search_query.strict:
        term_list = set([term.lower() for term in search_query.query.split()])
        logging.debug(f"Strict mode enabled, title must contain: {term_list}")

    results_count = len(results_soup)
    logging.debug(f"{results_count} results found")

    output = get_top_level_feed(base_url, search_query)

    if response_soup.find(id='captchacharacters'):
        logging.error('Catpcha triggered, blocked')
        return output

    items = []

    for item_soup in results_soup:
        asin = item_soup['data-asin']
        item_url = f"{base_url}/dp/{asin}"

        # use wildcard CSS selector for better compatibility
        item_title_soup = item_soup.select_one("[class*='s-line-clamp-']")
        item_title = item_title_soup.text.strip() if item_title_soup else ''

        item_price_soup = item_soup.select_one('.a-price .a-offscreen')
        item_price = item_price_soup.text.strip() if item_price_soup else None
        item_price_text = item_price if item_price else 'Out of SRP'

        item_thumbnail_soup = item_soup.find(
            attrs={'data-component-type': 's-product-image'})
        item_thumbnail_img_soup = item_thumbnail_soup.select_one('.s-image')
        item_thumbnail_url = item_thumbnail_img_soup.get(
            'src') if item_thumbnail_img_soup else None

        content_body = f'<img src=\"{item_thumbnail_url}\" />'

        timestamp = datetime.now().timestamp()

        item = {
            'id': datetime.utcfromtimestamp(timestamp).isoformat('T'),
            'url': item_url,
            'title': f"[{item_price_text}] {item_title}",
            'content_html': bleach.clean(
                content_body,
                tags=allowed_tags,
                attributes=allowed_attributes,
                styles=allowed_styles
            ),
            'image': item_thumbnail_url,
            'date_published': datetime.utcfromtimestamp(timestamp).isoformat('T')
        }

        if search_query.srp_only and not item_price:
            logging.debug(f'SRP only enabled, item "{item_title}" removed')
        elif search_query.strict and (term_list and not all(item_title.lower().find(term) >= 0 for term in term_list)):
            logging.debug(f'Strict mode enabled, item "{item_title}" removed')
        else:
            items.append(item)

    output['items'] = items
    logging.debug(f"{len(items)} results published")

    return output
