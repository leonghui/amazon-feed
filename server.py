from flask import Flask, request, jsonify, abort
from flask.logging import create_logger

from amazon_feed import get_search_results
from amazon_feed_data import AmazonSearchQuery


app = Flask(__name__)
logger = create_logger(app)


def string_to_boolean(string):
    return string.lower().strip() in ['yes', 'true']


def process_query():
    query_text = request.args.get('query')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    country_text = request.args.get('country')
    buybox_only_text = request.args.get('buybox_only')
    strict_text = request.args.get('strict')

    if not isinstance(query_text, str):
        abort(400, description='Please provide a valid query string.')

    if min_price and not min_price.isnumeric():
        abort(400, description='Invalid min price.')

    if max_price and not max_price.isnumeric():
        abort(400, description='Invalid max price.')

    country = country_text.upper() if isinstance(
        country_text, str) and len(country_text) == 2 else 'US'

    buybox_only = True if isinstance(
        buybox_only_text, str) and string_to_boolean(buybox_only_text) else False

    strict = True if isinstance(
        strict_text, str) and string_to_boolean(strict_text) else False

    search_query = AmazonSearchQuery(
        query_text, country, buybox_only, strict, min_price, max_price)

    logger.debug(search_query)  # log values

    try:
        output = get_search_results(search_query, logger)
        response = jsonify(output)
        response.mimetype = 'application/feed+json'
        return response
    except Exception:
        abort(500, description='Error generating output')



@app.route('/', methods=['GET'])
def home():
    return process_query()


@app.route('/search', methods=['GET'])
def search():
    return process_query()


if __name__ == '__main__':
    app.run(host='0.0.0.0')
