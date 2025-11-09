from logging import Logger, getLogger

from curl_cffi import Response, Session
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from config.constants import DEFAULT_USER_AGENT
from models.feed import JsonFeedItem, JsonFeedTopLevel
from models.query import (
    AmazonAsinQuery,
    AmazonKeywordQuery,
    QueryConfig,
    QueryParams,
    QueryStatus,
)
from models.validators import convert_to_locale
from parsers.item_parser import parse_item_details
from parsers.search_parser import parse_search_results
from services.item_generator import get_top_level_feed
from services.response_handler import get_response
from services.url_builder import get_dimension_url, get_search_url

app: FastAPI = FastAPI()
logger: Logger = getLogger(name="uvicorn.error")


class AmazonFeedGenerator:
    def __init__(self) -> None:
        """
        Initialize the Amazon Feed Generator with configuration and setup.
        """
        # Setup can be done here if needed

    def create_query_config(self) -> QueryConfig:
        return QueryConfig(
            session=Session(),
            logger=logger,
            useragent=DEFAULT_USER_AGENT,
        )


feed_generator: AmazonFeedGenerator = AmazonFeedGenerator()


@app.get(path="/")
@app.get(path="/query")
async def keyword_search(params: QueryParams = Depends()) -> JSONResponse:
    """
    Handle keyword search requests.
    """
    try:
        config: QueryConfig = feed_generator.create_query_config()

        query: AmazonKeywordQuery = AmazonKeywordQuery(
            status=QueryStatus(),
            query_str=params.q,
            locale=convert_to_locale(value=params.country),
            min_price=params.min_price,
            max_price=params.max_price,
            strict=params.strict,
            config=config,
        )

        base_url: str = f"https://{query.locale.domain}"
        search_url: str = get_search_url(base_url, query)

        response: Response | JSONResponse = get_response(url=search_url, query=query)

        if isinstance(response, Response):
            feed_items: list[JsonFeedItem] = parse_search_results(
                response.content, query, base_url
            )

            json_feed: JsonFeedTopLevel = get_top_level_feed(
                base_url, query, feed_items
            )

            return JSONResponse(content=json_feed.model_dump(exclude_none=True))
        else:
            return response

    except Exception as e:
        logger.error(msg=f"Keyword search error: {e}")
        raise HTTPException(status_code=500, detail=f"Keyword search error: {e}")


@app.get(path="/asin")
async def asin_lookup(params: QueryParams = Depends()) -> JSONResponse:
    """
    Handle ASIN lookup requests.
    """
    try:
        config: QueryConfig = feed_generator.create_query_config()

        query: AmazonAsinQuery = AmazonAsinQuery(
            status=QueryStatus(),
            query_str=params.q,
            locale=convert_to_locale(value=params.country),
            min_price=params.min_price,
            max_price=params.max_price,
            config=config,
        )

        base_url: str = f"https://{query.locale.domain}"
        search_url: str = get_dimension_url(query)

        response: Response | JSONResponse = get_response(url=search_url, query=query)

        if isinstance(response, Response):
            feed_items: list[JsonFeedItem] = parse_item_details(
                response.json(), query, base_url
            )

            json_feed: JsonFeedTopLevel = get_top_level_feed(
                base_url, query, feed_items
            )

            return JSONResponse(content=json_feed.model_dump(exclude_none=True))
        else:
            return response

    except Exception as e:
        logger.error(msg=f"ASIN lookup error: {e}")
        raise HTTPException(status_code=500, detail=f"ASIN lookup error: {e}")


@app.get(path="/healthcheck")
async def healthcheck() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
