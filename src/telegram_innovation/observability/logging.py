"""Allowlist-only JSON logs: messages, exceptions and identifiers never serialize."""

import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

FIELDS = {"event", "correlation", "operation", "outcome", "duration_ms", "error_code", "count"}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        result: dict[str, str | int | float | bool] = {
            "time": datetime.now(UTC).isoformat(),
            "level": record.levelname,
        }
        # No getMessage(), exception text, request URLs, user content, or arbitrary extras.
        for key in FIELDS:
            value = getattr(record, key, None)
            if isinstance(value, (str, int, float, bool)):
                result[key] = value
        return json.dumps(result, separators=(",", ":"))


def configure(level: str = "INFO", path: str | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        handlers.append(RotatingFileHandler(destination, maxBytes=1048576, backupCount=5))
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(level)
    for handler in handlers:
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    # Even debugging HTTP clients must never emit token-bearing URLs.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).disabled = True
