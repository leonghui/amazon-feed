from logging import Logger

from curl_cffi import Response, Session
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from config.constants import DEFAULT_USER_AGENT
from models.feed import JsonFeedItem, JsonFeedTopLevel
from models.query import AmazonAsinQuery, AmazonKeywordQuery, QueryConfig, QueryStatus
from parsers.item_parser import parse_item_details
from parsers.search_parser import parse_search_results
from services.item_generator import get_top_level_feed
from services.response_handler import get_response
from services.url_builder import get_dimension_url, get_search_url
from utils.logging import setup_logger

app: FastAPI = FastAPI()
logger: Logger = setup_logger(name="amazon_feed_generator", level="INFO")


class AmazonFeedGenerator:
    def __init__(self) -> None:
        """
        Initialize the Amazon Feed Generator with configuration and setup.
        """
        # Setup can be done here if needed

    def create_query_config(self) -> QueryConfig:
        session: Session = Session()

        return QueryConfig(
            session=session,
            logger=logger,
            useragent=DEFAULT_USER_AGENT,
        )


feed_generator: AmazonFeedGenerator = AmazonFeedGenerator()


@app.get("/")
@app.get("/query")
async def keyword_search(
    q: str = Query(..., description="Search query"),
    country: str = Query("us", description="Country code"),
    min_price: str = Query(None, description="Minimum price"),
    max_price: str = Query(None, description="Maximum price"),
    strict: bool = Query(False, description="Strict mode"),
) -> JSONResponse:
    """
    Handle keyword search requests.
    """
    try:
        config: QueryConfig = feed_generator.create_query_config()

        query: AmazonKeywordQuery = AmazonKeywordQuery(
            status=QueryStatus(),
            query_str=q,
            country=country,
            min_price=min_price,
            max_price=max_price,
            strict=strict,
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

            return JSONResponse(content=json_feed)
        else:
            return response

    except Exception as e:
        logger.error(msg=f"Keyword search error: {e}")
        raise HTTPException(status_code=500, detail=f"Keyword search error: {e}")


@app.get("/asin")
async def asin_lookup(
    q: str = Query(..., description="ASIN to look up"),
    country: str = Query("us", description="Country code"),
    min_price: str = Query(None, description="Minimum price"),
    max_price: str = Query(None, description="Maximum price"),
) -> JSONResponse:
    """
    Handle ASIN lookup requests.
    """
    try:
        config: QueryConfig = feed_generator.create_query_config()

        query: AmazonAsinQuery = AmazonAsinQuery(
            status=QueryStatus(),
            query_str=q,
            country=country,
            min_price=min_price,
            max_price=max_price,
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

            return JSONResponse(content=json_feed)
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
