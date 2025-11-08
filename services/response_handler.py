from logging import Logger
import re

from curl_cffi.requests.exceptions import RequestException
from flask import abort
from curl_cffi import Response, Session

from config.constants import CFFI_IMPERSONATE, HEADERS
from models.query import FilterableQuery


def clear_session_cookies(query: FilterableQuery) -> None:
    """Clear session cookies for the given query."""
    query.config.session.cookies.clear()


def get_response(url: str, query: FilterableQuery) -> Response:
    """
    Send a GET request with error handling and bot detection.

    Handles:
    - Request exceptions
    - Bot detection
    - HTTP error responses
    """
    logger: Logger = query.config.logger
    session: Session = query.config.session

    # Prepare headers
    headers: dict[str, str] = HEADERS.copy()
    headers["User-Agent"] = query.config.useragent
    headers["Referer"] = f"https://{query.locale.domain}/"

    logger.debug(msg=f"{query.query_str} - querying: {url}")

    try:
        response: Response = session.get(
            url, impersonate=CFFI_IMPERSONATE, default_headers=False, headers=headers
        )
    except RequestException as rex:
        clear_session_cookies(query)
        logger.error(msg=f"{query.query_str} - Request error: {rex}")
        abort(code=500)

    # Bot/paywall detection
    bot_patterns: list[str] = [
        r"bot",
        r"captcha",
        r"challenge",
        r"verify",
        r"blocked",
        r"automated",
    ]

    if not response.ok:
        # Paywall or bot detection
        if response.status_code == 503 or any(
            re.search(pattern, response.text, re.IGNORECASE) for pattern in bot_patterns
        ):
            bot_msg: str = f"{query.query_str} - API paywall or bot detection"
            clear_session_cookies(query)
            logger.warning(msg=bot_msg)
            abort(code=429, description=bot_msg)

        # Other HTTP errors
        logger.error(msg=f"{query.query_str} - HTTP error: {response.status_code}")
        logger.debug(msg=f"Response text: {response.text}")
        abort(code=500)

    # Log caching status
    logger.debug(msg=f"{query.query_str}")
    return response
