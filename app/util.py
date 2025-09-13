import logging

from rich.logging import RichHandler

from app.config import settings


def setup_logging():
    """
    Setup logging configuration.
    """
    logger = logging.getLogger()
    logger.handlers = []  # Clear any existing handlers
    logging.basicConfig(
        level=logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO,
        handlers=[RichHandler()],
    )
