from __future__ import annotations

from collections.abc import Iterable

from .apple_mobileconfig import build_apple_mobileconfig, safe_filename_part
from .settings import Gateway


def build_ios_mobileconfig(
    username: str,
    password: str,
    vpn_shared_psk: str,
    gateways: Iterable[Gateway],
) -> bytes:
    return build_apple_mobileconfig(
        username=username,
        password=password,
        vpn_shared_psk=vpn_shared_psk,
        gateways=gateways,
        platform_key="ios",
        payload_scope=None,
    )


def ios_profile_filename(username: str) -> str:
    return f"wormhole-{safe_filename_part(username)}-ios.mobileconfig"
