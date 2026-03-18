from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    admin_username: str
    admin_password: str
    session_secret: str
    bind_port: int
    ca_api_url: str
    ca_api_token: str
    timezone_name: str
    p12_export_password: str
    log_level: str
    log_dir_root: Path


def load_settings() -> Settings:
    return Settings(
        db_host=os.getenv("DB_HOST", "db"),
        db_port=_as_int("DB_PORT", 3306),
        db_name=os.getenv("DB_NAME", "radius"),
        db_user=os.getenv("DB_USER", "radius"),
        db_password=os.getenv("DB_PASSWORD", ""),
        admin_username=os.getenv("ADMIN_USERNAME", "admin"),
        admin_password=os.getenv("ADMIN_PASSWORD", ""),
        session_secret=os.getenv("ADMIN_SESSION_SECRET", "change-me"),
        bind_port=_as_int("ADMIN_BIND_PORT", 8000),
        ca_api_url=os.getenv("CA_API_URL", "http://ca-api:9000"),
        ca_api_token=os.getenv("CA_API_TOKEN", ""),
        timezone_name=os.getenv("APP_TIMEZONE", "UTC"),
        p12_export_password=os.getenv("P12_EXPORT_PASSWORD", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir_root=Path(os.getenv("LOG_DIR_ROOT", "/var/log/wormhole")),
    )
