from __future__ import annotations

import plistlib
import re
from collections.abc import Iterable
from uuid import NAMESPACE_URL, uuid5

from .settings import Gateway

L2TP_PROTOCOL = "l2tp-ipsec-psk"
PROFILE_NAMESPACE = uuid5(NAMESPACE_URL, "https://wormhole.local/macos-vpn-profile")


def _stable_uuid(value: str) -> str:
    return str(uuid5(PROFILE_NAMESPACE, value)).upper()


def safe_filename_part(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return sanitized or "account"


def build_apple_mobileconfig(
    username: str,
    password: str,
    vpn_shared_psk: str,
    gateways: Iterable[Gateway],
    *,
    platform_key: str,
    payload_scope: str | None,
) -> bytes:
    l2tp_gateways = tuple(gateway for gateway in gateways if gateway.protocol == L2TP_PROTOCOL)
    if not l2tp_gateways:
        raise ValueError("no L2TP/IPSec gateway configured")

    profile_key = f"wormhole-{platform_key}:{username}"
    profile_identifier = f"com.wormhole.vpn.{uuid5(PROFILE_NAMESPACE, profile_key).hex}"
    multiple_gateways = len(l2tp_gateways) > 1
    payloads = []

    for gateway in l2tp_gateways:
        payload_key = f"{profile_key}:{gateway.name}:{gateway.address}"
        display_name = f"Wormhole - {gateway.name}" if multiple_gateways else "Wormhole VPN"
        payload = {
            "PayloadDescription": f"L2TP/IPSec VPN for {username}",
            "PayloadDisplayName": display_name,
            "PayloadIdentifier": f"{profile_identifier}.{uuid5(PROFILE_NAMESPACE, payload_key).hex}",
        }
        if payload_scope is not None:
            payload["PayloadScope"] = payload_scope
        payload.update(
            {
                "PayloadType": "com.apple.vpn.managed",
                "PayloadUUID": _stable_uuid(payload_key),
                "PayloadVersion": 1,
                "UserDefinedName": display_name,
                "VPNType": "L2TP",
                "PPP": {
                    "AuthName": username,
                    "AuthPassword": password,
                    "CommRemoteAddress": gateway.address,
                    "TokenCard": 0,
                },
                "IPSec": {
                    "AuthenticationMethod": "SharedSecret",
                    "RemoteAddress": gateway.address,
                    "SharedSecret": vpn_shared_psk.encode("utf-8"),
                },
                "IPv4": {"OverridePrimary": 1},
                "Proxies": {"HTTPEnable": 0, "HTTPSEnable": 0},
            }
        )
        payloads.append(payload)

    profile = {
        "PayloadContent": payloads,
        "PayloadDescription": f"Wormhole VPN connections for {username}",
        "PayloadDisplayName": f"Wormhole VPN - {username}",
        "PayloadIdentifier": profile_identifier,
        "PayloadOrganization": "Wormhole VPN",
        "PayloadRemovalDisallowed": False,
        "PayloadType": "Configuration",
        "PayloadUUID": _stable_uuid(profile_key),
        "PayloadVersion": 1,
    }
    return plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False)
