from __future__ import annotations

import secrets
import string
import subprocess
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo


def hash_vpn_password(password: str) -> str:
    salt = "".join(secrets.choice(string.ascii_letters + string.digits + "./") for _ in range(16))
    result = subprocess.run(
        ["openssl", "passwd", "-6", "-salt", salt, password],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def to_utc_naive_end_of_day(date_value: str, timezone_name: str) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_date = datetime.strptime(date_value, "%Y-%m-%d").date()
    local_dt = datetime.combine(local_date, time(23, 59, 59), tzinfo=zone)
    return local_dt.astimezone(UTC).replace(tzinfo=None)


def format_radius_expiration(value: datetime) -> str:
    return value.replace(tzinfo=UTC).strftime("%d %b %Y %H:%M:%S UTC")


def effective_radius_expiration(status: str, expiration_at: datetime) -> datetime:
    if status == "enabled":
        return expiration_at
    return datetime.now(UTC).replace(tzinfo=None)


def next_available_slot(active_slots: set[int], max_slots: int = 2) -> int | None:
    for slot_no in range(1, max_slots + 1):
        if slot_no not in active_slots:
            return slot_no
    return None
