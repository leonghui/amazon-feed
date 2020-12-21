from flask import Flask, request, jsonify
from requests import exceptions

from amazon_feed import get_listing
from amazon_search_query_class import AmazonSearchQueryClass


app = Flask(__name__)


def string_to_boolean(string):
    return string.lower().strip() in ['yes', 'true']


@app.route('/', methods=['GET'])
def form():
    query_text = request.args.get('query')
    node_id = request.args.get('node_id')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    country_text = request.args.get('country')
    srp_only_text = request.args.get('srp_only')
    strict_text = request.args.get('strict')

    if not isinstance(query_text, str):
        return 'Please provide a valid query string.'

    if node_id and not isinstance(node_id, str):
        return 'Please provide a valid node id.'

    if min_price and not min_price.isnumeric():
        return 'Invalid min price.'

    if max_price and not max_price.isnumeric():
        return 'Invalid max price.'

    country = None

    if country_text:
        if isinstance(country_text, str) and len(country_text) == 2:
            country = country_text.upper()
    else:
        country = 'US'

    srp_only = True if isinstance(
        srp_only_text, str) and string_to_boolean(srp_only_text) else False

    strict = True if isinstance(
        strict_text, str) and string_to_boolean(strict_text) else False

    search_query = AmazonSearchQueryClass(
        query_text, node_id, country, min_price, max_price, srp_only, strict)

    try:
        output = get_listing(search_query)
        return jsonify(output)
    except exceptions.RequestException:
        return f"Error generating output for query {query_text}."


if __name__ == '__main__':
    app.run(host='0.0.0.0')
