from __future__ import annotations

import logging
import time
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from .settings import Settings

logger = logging.getLogger("wormhole.app")


def connect(settings: Settings):
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        cursorclass=DictCursor,
        autocommit=False,
        charset="utf8mb4",
    )


@contextmanager
def transaction(settings: Settings):
    connection = connect(settings)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def wait_for_db(settings: Settings, retries: int = 20, delay_seconds: int = 2) -> None:
    last_error = None
    for _ in range(retries):
        try:
            connection = connect(settings)
            connection.close()
            logger.info("database_ready host=%s port=%s", settings.db_host, settings.db_port)
            return
        except Exception as exc:  # pragma: no cover - startup-only branch
            last_error = exc
            logger.warning("database_not_ready host=%s port=%s error=%s", settings.db_host, settings.db_port, exc)
            time.sleep(delay_seconds)
    raise RuntimeError("database not reachable") from last_error
