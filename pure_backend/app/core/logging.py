import json
import logging
from datetime import datetime, timezone

from app.core.config import Settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(settings: Settings) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    if settings.log_format.lower() == "json":
        stream_handler.setFormatter(JsonFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )

    root_logger.addHandler(stream_handler)
