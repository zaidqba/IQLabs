"""
IQ-RAD Structured JSON Logging Configuration
All log entries include timestamp, level, module, request_id, and user context
where available. This supports audit correlation and incident investigation.
"""
import logging
import sys
from typing import Any

import orjson


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON for structured log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        # Include extra fields set on the log record
        for key in ("request_id", "user_id", "user_name", "device_id", "channel_id"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return orjson.dumps(log_data).decode()


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logger with JSON formatter for production use."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.handlers = [handler]

    # Suppress noisy third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
