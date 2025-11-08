from http import HTTPStatus
from logging import Logger

from flask import Flask, Response as FlaskResponse, jsonify, request
from requests import Response, Session
from requests.sessions import Session

from config.constants import DEFAULT_USER_AGENT
from config.curl_adapter import curl_cffi_adapter
from models.feed import JsonFeedItem, JsonFeedTopLevel
from models.query import AmazonAsinQuery, AmazonKeywordQuery, QueryConfig, QueryStatus
from parsers.item_parser import parse_item_details
from parsers.search_parser import parse_search_results
from services.item_generator import get_top_level_feed
from services.response_handler import get_response
from services.url_builder import get_dimension_url, get_search_url
from utils.logging import setup_logger

class AmazonFeedGenerator:
    def __init__(self) -> None:
        """
        Initialize the Amazon Feed Generator with configuration and setup.
        """
        # Flask application setup
        self.app: Flask = Flask(import_name=__name__)

        # Configure routes
        self.setup_routes()

        # Logging setup
        self.logger: Logger = setup_logger(name="amazon_feed_generator", level="INFO")

    def setup_routes(self) -> None:
        """
        Define API routes for the application.
        """
        self.app.route(rule="/query", methods=["GET"])(self.keyword_search)
        self.app.route(rule="/asin", methods=["GET"])(self.asin_lookup)
        self.app.route(rule="/healthcheck", methods=["GET"])(self.healthcheck)

    def create_query_config(self) -> QueryConfig:
        session: Session = Session()
        session.mount(prefix="http://", adapter=curl_cffi_adapter)
        session.mount(prefix="https://", adapter=curl_cffi_adapter)

        return QueryConfig(
            session=session,
            logger=self.logger,
            useragent=DEFAULT_USER_AGENT,
        )

    def keyword_search(self) -> tuple[FlaskResponse, int]:
        """
        Handle keyword search requests.

        Returns:
            dict: JSON feed of search results
        """
        try:
            # Extract parameters
            query_str: str = request.args.get("q", "")
            country: str = request.args.get("country", "us")
            min_price: str | None = request.args.get("min_price", "")
            max_price: str | None = request.args.get("max_price", "")
            strict: bool = request.args.get("strict", "false").lower() == "true"

            # Validate input
            if not query_str:
                return jsonify(
                    {"error": "Query string is required"}
                ), HTTPStatus.BAD_REQUEST

            # Create query configuration
            config: QueryConfig = self.create_query_config()

            # Create keyword query
            query: AmazonKeywordQuery = AmazonKeywordQuery(
                status=QueryStatus(),
                query_str=query_str,
                country=country,
                min_price=min_price,
                max_price=max_price,
                strict=strict,
                config=config,
            )

            # Perform search and generate feed
            base_url: str = f"https://{query.locale.domain}"
            search_url: str = get_search_url(base_url, query)

            response: Response = get_response(url=search_url, query=query)
            feed_items: list[JsonFeedItem] = parse_search_results(
                response.content, query, base_url
            )

            json_feed: JsonFeedTopLevel = get_top_level_feed(
                base_url, query, feed_items
            )

            return jsonify(json_feed), HTTPStatus.OK

        except Exception as e:
            self.logger.error(msg=f"Keyword search error: {e}")
            return jsonify(
                {"error": f"Keyword search error: {e}"}
            ), HTTPStatus.INTERNAL_SERVER_ERROR

    def asin_lookup(self) -> tuple[FlaskResponse, int]:
        """
        Handle ASIN lookup requests.

        Returns:
            dict: JSON feed of search result
        """
        try:
            # Extract parameters
            query_str: str = request.args.get("q", "")
            country: str = request.args.get("country", "us")
            min_price: str | None = request.args.get("min_price", "")
            max_price: str | None = request.args.get("max_price", "")

            # Validate input
            if not query_str:
                return jsonify(
                    {"error": "Query string is required"}
                ), HTTPStatus.BAD_REQUEST

            # Create query configuration
            config: QueryConfig = self.create_query_config()

            # Create keyword query
            query: AmazonAsinQuery = AmazonAsinQuery(
                status=QueryStatus(),
                query_str=query_str,
                country=country,
                min_price=min_price,
                max_price=max_price,
                config=config,
            )

            # Perform search and generate feed
            base_url: str = f"https://{query.locale.domain}"
            search_url: str = get_dimension_url(query)

            response: Response = get_response(url=search_url, query=query)
            feed_items: list[JsonFeedItem] = parse_item_details(
                response.json(), query, base_url
            )

            json_feed: JsonFeedTopLevel = get_top_level_feed(
                base_url, query, feed_items
            )

            return jsonify(json_feed), HTTPStatus.OK

        except Exception as e:
            self.logger.error(msg=f"ASIN lookup error: {e}")
            return jsonify(
                {"error": f"ASIN lookup error: {e}"}
            ), HTTPStatus.INTERNAL_SERVER_ERROR

    def healthcheck(self) -> tuple[FlaskResponse, int]:
        return jsonify({"status": "ok"}), HTTPStatus.OK


if __name__ == "__main__":
    feed_generator: AmazonFeedGenerator = AmazonFeedGenerator()
    feed_generator.app.run(host="0.0.0.0")
