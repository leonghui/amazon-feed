from logging import Logger, getLogger
from typing import Any

from curl_cffi import Response as CurlResponse, Session
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response

from config.constants import DEFAULT_USER_AGENT
from models.feed import JsonFeedTopLevel
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
from services.ld_generator import get_html
from services.response_handler import get_response
from services.url_builder import get_dimension_url, get_search_url

app: FastAPI = FastAPI()
logger: Logger = getLogger(name="uvicorn.error")


class AmazonFeedGenerator:
    def create_query_config(self) -> QueryConfig:
        return QueryConfig(
            session=Session(),
            logger=logger,
            useragent=DEFAULT_USER_AGENT,
        )

    def process_query(
        self,
        params: QueryParams,
        query_class: type[AmazonKeywordQuery | AmazonAsinQuery],
        url_builder_func,
        parser_func,
    ) -> Response:
        try:
            config: QueryConfig = self.create_query_config()

            query: AmazonAsinQuery | AmazonKeywordQuery = query_class(
                status=QueryStatus(),
                query_str=params.q,
                locale=convert_to_locale(value=params.country),
                min_price=params.min_price,
                max_price=params.max_price,
                jsonld=params.jsonld,
                config=config,
            )

            base_url: str = f"https://{query.locale.domain}"
            search_url: Any = url_builder_func(base_url, query)

            response: CurlResponse | JSONResponse = get_response(
                url=search_url, query=query
            )

            if isinstance(response, CurlResponse):
                feed_items: list = parser_func(
                    response.content or response.json(), query, base_url
                )

                if params.jsonld:
                    html_text: str = get_html(feed_items)
                    return HTMLResponse(content=html_text)
                else:
                    json_feed: JsonFeedTopLevel = get_top_level_feed(
                        base_url, query, feed_items
                    )
                    return JSONResponse(content=json_feed.model_dump(exclude_none=True))

            return response

        except Exception as e:
            error_msg: str = f"{'Keyword' if query_class is AmazonKeywordQuery else 'ASIN'} lookup error: {e}"
            logger.error(msg=error_msg)
            raise HTTPException(status_code=500, detail=error_msg)


feed_generator: AmazonFeedGenerator = AmazonFeedGenerator()


@app.get(path="/")
@app.get(path="/query")
async def keyword_search(params: QueryParams = Depends()) -> Response:
    return feed_generator.process_query(
        params,
        query_class=AmazonKeywordQuery,
        url_builder_func=get_search_url,
        parser_func=parse_search_results,
    )


@app.get(path="/asin")
async def asin_lookup(params: QueryParams = Depends()) -> Response:
    return feed_generator.process_query(
        params,
        query_class=AmazonAsinQuery,
        url_builder_func=get_dimension_url,
        parser_func=parse_item_details,
    )


@app.get(path="/healthcheck")
async def healthcheck() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
