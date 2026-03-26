"""Basic seed/bootstrap placeholder for future domain initialization."""

import logging

from app.core.config import get_settings
from app.core.logging import setup_logging


def main() -> None:
    settings = get_settings()
    setup_logging(settings)
    logger = logging.getLogger(__name__)
    logger.info("Seed bootstrap placeholder executed")


if __name__ == "__main__":
    main()
