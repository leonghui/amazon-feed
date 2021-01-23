from flask import Flask, request, jsonify, abort
from flask.logging import create_logger

from amazon_feed import get_search_results, get_item_listing
from amazon_feed_data import AmazonSearchQuery, AmazonListQuery, QueryStatus
from mozilla_devices import get_useragent_list, DeviceType


app = Flask(__name__)
app.config.update({'JSONIFY_MIMETYPE': 'application/feed+json'})
logger = create_logger(app)
useragent_list = get_useragent_list(DeviceType.PHONES, logger)


def generate_response(query_object):
    if not query_object.status.ok:
        abort(400, description='Errors found: ' +
              ', '.join(query_object.status.errors))

    logger.debug(query_object)  # log values

    if isinstance(query_object, AmazonSearchQuery):
        output = get_search_results(query_object, useragent_list, logger)
    elif isinstance(query_object, AmazonListQuery):
        output = get_item_listing(query_object, useragent_list, logger)
    return jsonify(output)


@app.route('/', methods=['GET'])
@app.route('/search', methods=['GET'])
def process_query():
    query = request.args.get('query')
    country = request.args.get('country')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    strict = request.args.get('strict')

    search_query = AmazonSearchQuery(
        query=query,
        country=country,
        min_price=min_price,
        max_price=max_price,
        strict=strict,
        status=QueryStatus()
    )

    return generate_response(search_query)


@app.route('/item', methods=['GET'])
def process_listing():
    query = request.args.get('id')
    country = request.args.get('country')
    min_price = None
    max_price = request.args.get('max_price')

    list_query = AmazonListQuery(
        query=query,
        country=country,
        min_price=min_price,
        max_price=max_price,
        status=QueryStatus()
    )

    return generate_response(list_query)


if __name__ == '__main__':
    app.run(host='0.0.0.0', use_reloader=False)
