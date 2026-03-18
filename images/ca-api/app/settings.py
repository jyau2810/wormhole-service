from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    bind_port: int
    token: str
    data_dir: Path
    timezone_name: str
    ca_common_name: str
    ca_organization: str
    ca_validity_days: int
    server_cert_validity_days: int
    client_cert_validity_days: int
    vpn_server_host: str
    vpn_server_alt_names: list[str]
    p12_export_password: str
    log_level: str
    log_dir_root: Path


def load_settings() -> Settings:
    alt_names = [
        item.strip()
        for item in os.getenv("VPN_SERVER_ALT_NAMES", "").split(",")
        if item.strip()
    ]
    return Settings(
        bind_port=_as_int("INTERNAL_API_BIND_PORT", 9000),
        token=os.getenv("CA_API_TOKEN", ""),
        data_dir=Path(os.getenv("CA_DATA_DIR", "/data")),
        timezone_name=os.getenv("APP_TIMEZONE", "UTC"),
        ca_common_name=os.getenv("CA_COMMON_NAME", "Wormhole VPN Internal CA"),
        ca_organization=os.getenv("CA_ORGANIZATION", "Wormhole VPN"),
        ca_validity_days=_as_int("CA_VALIDITY_DAYS", 3650),
        server_cert_validity_days=_as_int("SERVER_CERT_VALIDITY_DAYS", 825),
        client_cert_validity_days=_as_int("CLIENT_CERT_VALIDITY_DAYS", 365),
        vpn_server_host=os.getenv("VPN_SERVER_HOST", "vpn.example.com"),
        vpn_server_alt_names=alt_names,
        p12_export_password=os.getenv("P12_EXPORT_PASSWORD", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir_root=Path(os.getenv("LOG_DIR_ROOT", "/var/log/wormhole")),
    )
