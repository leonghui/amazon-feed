from logging import Formatter, Logger, StreamHandler
import logging
from typing import TextIO


def setup_logger(
    name: str = "amazon_feed",
    level: int | str = logging.INFO,
) -> logging.Logger:

    # Create logger
    logger: Logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers to prevent duplicate logging
    logger.handlers.clear()

    # Console handler
    console_handler: StreamHandler[TextIO] = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format: Formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(fmt=console_format)
    logger.addHandler(hdlr=console_handler)

    return logger
