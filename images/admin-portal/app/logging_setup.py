from __future__ import annotations

import logging
import logging.config
from contextvars import ContextVar
from pathlib import Path

from .settings import Settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")
        return True


def configure_logging(settings: Settings) -> None:
    log_dir = settings.log_dir_root / "admin-portal"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_context": {
                    "()": "app.logging_setup.RequestContextFilter",
                }
            },
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_context"],
                },
                "app_file": {
                    "class": "logging.handlers.WatchedFileHandler",
                    "filename": str(log_dir / "app.log"),
                    "formatter": "default",
                    "filters": ["request_context"],
                },
                "error_file": {
                    "class": "logging.handlers.WatchedFileHandler",
                    "filename": str(log_dir / "error.log"),
                    "formatter": "default",
                    "filters": ["request_context"],
                    "level": "ERROR",
                },
                "access_file": {
                    "class": "logging.handlers.WatchedFileHandler",
                    "filename": str(log_dir / "access.log"),
                    "formatter": "default",
                    "filters": ["request_context"],
                },
            },
            "root": {
                "level": settings.log_level,
                "handlers": ["console", "app_file", "error_file"],
            },
            "loggers": {
                "wormhole.access": {
                    "level": settings.log_level,
                    "handlers": ["console", "access_file"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "propagate": False,
                },
            },
        }
    )

