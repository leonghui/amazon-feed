from flask import Flask, abort, jsonify, request
from flask.logging import create_logger
from requests_cache import CachedSession

from amazon_feed import get_item_listing, get_keyword_results
from amazon_feed_data import (AmazonAsinQuery, AmazonKeywordQuery, FeedConfig,
                              FilterableQuery, QueryStatus)

CACHE_EXPIRATION_SEC = 60

app = Flask(__name__)
app.config.update({"JSONIFY_MIMETYPE": "application/json"})

# app.debug = True

config = FeedConfig(
    session=CachedSession(
        allowable_methods=("GET", "POST"),
        stale_if_error=True,
        expire_after=CACHE_EXPIRATION_SEC,
        backend="memory",
    ),
    logger=create_logger(app),
)

def generate_response(query: FilterableQuery):
    if not query.status.ok:
        abort(400, description="Errors found: " + ", ".join(query.status.errors))

    config.logger.debug(query)  # log values

    output = None

    if isinstance(query, AmazonKeywordQuery):
        output = get_keyword_results(query)
    elif isinstance(query, AmazonAsinQuery):
        output = get_item_listing(query)
    return jsonify(output)


@app.route("/", methods=["GET"])
@app.route("/search", methods=["GET"])
def process_listing():
    list_request_dict = {
        "query_str": request.args.get("query") or AmazonKeywordQuery.query_str,
        "country": request.args.get("country") or AmazonKeywordQuery.country,
        "min_price": request.args.get("min_price"),
        "max_price": request.args.get("max_price"),
        "strict_str": request.args.get("strict"),
    }

    listing_query = AmazonKeywordQuery(
        status=QueryStatus(), config=config, **list_request_dict
    )

    return generate_response(listing_query)


@app.route("/item", methods=["GET"])
def process_item():
    item_request_dict = {
        "query_str": request.args.get("id") or AmazonAsinQuery.query_str,
        "country": request.args.get("country") or AmazonAsinQuery.country,
        "min_price": None,
        "max_price": request.args.get("max_price"),
    }

    item_query = AmazonAsinQuery(
        status=QueryStatus(), config=config, **item_request_dict
    )

    return generate_response(item_query)


app.run(host="0.0.0.0")
