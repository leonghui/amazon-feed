from flask import Flask, request, jsonify, abort
from flask.logging import create_logger

from amazon_feed import get_search_results, get_item_listing
from amazon_feed_data import AmazonSearchQuery, AmazonListQuery, QueryStatus


app = Flask(__name__)
logger = create_logger(app)


def process_query():
    query_text = request.args.get('query')
    country = request.args.get('country')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    buybox_only_text = request.args.get('buybox_only')
    strict_text = request.args.get('strict')

    search_query = AmazonSearchQuery(QueryStatus(ok=True, errors=[]),
                                     query_text, country, min_price, max_price, buybox_only_text, strict_text)

    if not search_query.status.ok:
        abort(400, description='Errors found: ' +
              ', '.join(search_query.status.errors))

    logger.debug(search_query)  # log values

    output = get_search_results(search_query, logger)
    response = jsonify(output)
    response.mimetype = 'application/feed+json'
    return response


def process_listing():
    query = request.args.get('id')
    country = request.args.get('country')
    min_price = None
    max_price = request.args.get('max_price')

    list_query = AmazonListQuery(QueryStatus(ok=True, errors=[]),
                                 query, country, min_price, max_price)

    logger.debug(list_query)  # log values

    if not list_query.status.ok:
        abort(400, description='Errors found: ' +
              ', '.join(list_query.status.errors))

    output = get_item_listing(list_query, logger)
    response = jsonify(output)
    response.mimetype = 'application/feed+json'
    return response


@app.route('/', methods=['GET'])
def home():
    return process_query()


@app.route('/search', methods=['GET'])
def search():
    return process_query()


@app.route('/item', methods=['GET'])
def item():
    return process_listing()


if __name__ == '__main__':
    app.run(host='0.0.0.0')
