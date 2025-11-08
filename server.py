from typing import Any

from flask import abort, jsonify, request
from flask.app import Flask
from flask.logging import create_logger
from flask.wrappers import Response
from requests_cache import CachedSession

from amazon_feed import get_item_listing, get_keyword_results
from amazon_feed_data import (
    AmazonAsinQuery,
    AmazonKeywordQuery,
    FeedConfig,
    FilterableQuery,
    QueryStatus,
)

CACHE_EXPIRATION_SEC = 60

app: Flask = Flask(import_name=__name__)
app.config.update({"JSONIFY_MIMETYPE": "application/json"})

# app.debug = True

config: FeedConfig = FeedConfig(
    session=CachedSession(
        allowable_methods=("GET", "POST"),
        stale_if_error=True,
        expire_after=CACHE_EXPIRATION_SEC,
        backend="memory",
    ),
    logger=create_logger(app),
)


def generate_response(query: FilterableQuery) -> Response:
    if not query.status.ok:
        abort(code=400, description="Errors found: " + ", ".join(query.status.errors))

    config.logger.debug(msg=query)  # log values

    if isinstance(query, AmazonKeywordQuery):
        return jsonify(get_keyword_results(search_query=query))
    elif isinstance(query, AmazonAsinQuery):
        return jsonify(get_item_listing(query))
    else:
        return jsonify()


@app.route(rule="/", methods=["GET"])
@app.route(rule="/search", methods=["GET"])
def process_listing() -> Response:
    list_request_dict: dict[str, Any] = {
        "query_str": request.args.get("query") or AmazonKeywordQuery.query_str,
        "country": request.args.get("country") or AmazonKeywordQuery.country,
        "min_price": request.args.get("min_price"),
        "max_price": request.args.get("max_price"),
        "strict_str": request.args.get("strict"),
    }

    listing_query: AmazonKeywordQuery = AmazonKeywordQuery(
        status=QueryStatus(), config=config, **list_request_dict
    )

    return generate_response(query=listing_query)


@app.route(rule="/item", methods=["GET"])
def process_item() -> Response:
    item_request_dict: dict[str, Any] = {
        "query_str": request.args.get("id") or AmazonAsinQuery.query_str,
        "country": request.args.get("country") or AmazonAsinQuery.country,
        "min_price": None,
        "max_price": request.args.get("max_price"),
    }

    item_query: AmazonAsinQuery = AmazonAsinQuery(
        status=QueryStatus(), config=config, **item_request_dict
    )

    return generate_response(query=item_query)


app.run(host="0.0.0.0")
