from __future__ import annotations

import re
from pathlib import Path

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_ocserv_username(username: str) -> None:
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("username must use 1-64 letters, digits, dots, underscores, or hyphens")


def render_ocserv_user_policy(speed_profile: dict, max_concurrent_sessions: int) -> str:
    max_up_bps = int(speed_profile["max_up_kbps"]) * 1000 // 8
    max_down_bps = int(speed_profile["max_down_kbps"]) * 1000 // 8
    return (
        f"max-same-clients = {int(max_concurrent_sessions)}\n"
        f"rx-data-per-sec = {max_up_bps}\n"
        f"tx-data-per-sec = {max_down_bps}\n"
    )


def sync_ocserv_user_policy(
    config_dir: Path,
    username: str,
    speed_profile: dict,
    max_concurrent_sessions: int,
) -> None:
    validate_ocserv_username(username)
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / username).write_text(
        render_ocserv_user_policy(speed_profile, max_concurrent_sessions),
        encoding="utf-8",
    )
