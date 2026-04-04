from __future__ import annotations

import json
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
    timezone_name: str
    log_level: str
    log_dir_root: Path
    vpn_shared_psk: str
    vpn_default_speed_profile: str
    vpn_max_concurrent_sessions: int
    vpn_gateways: tuple["Gateway", ...]


@dataclass(frozen=True)
class Gateway:
    name: str
    address: str
    protocol: str
    port: int
    priority: int
    notes: str = ""


def _parse_gateways() -> tuple[Gateway, ...]:
    raw = os.getenv("VPN_GATEWAYS", "").strip()
    if not raw:
        legacy_host = os.getenv("VPN_SERVER_HOST", "vpn.example.com")
        return (
            Gateway(
                name="default-l2tp",
                address=legacy_host,
                protocol="l2tp-ipsec-psk",
                port=_as_int("VPN_L2TP_PORT", 1701),
                priority=10,
                notes="Default native VPN gateway",
            ),
        )

    items = json.loads(raw)
    gateways: list[Gateway] = []
    for index, item in enumerate(items):
        gateways.append(
            Gateway(
                name=item["name"],
                address=item["address"],
                protocol=item.get("protocol", "l2tp-ipsec-psk"),
                port=int(item.get("port", 1701)),
                priority=int(item.get("priority", index + 1)),
                notes=item.get("notes", ""),
            )
        )
    gateways.sort(key=lambda gateway: (gateway.priority, gateway.name))
    return tuple(gateways)


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
        bind_port=8000,
        timezone_name=os.getenv("APP_TIMEZONE", "UTC"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir_root=Path(os.getenv("LOG_DIR_ROOT", "/var/log/wormhole")),
        vpn_shared_psk=os.getenv("VPN_SHARED_PSK", ""),
        vpn_default_speed_profile=os.getenv("VPN_DEFAULT_SPEED_PROFILE", "standard-10m"),
        vpn_max_concurrent_sessions=_as_int("VPN_MAX_CONCURRENT_SESSIONS", 1),
        vpn_gateways=_parse_gateways(),
    )
