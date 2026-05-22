from __future__ import annotations

from collections.abc import Iterable

from .settings import Gateway

L2TP_PROTOCOL = "l2tp-ipsec-psk"
UNICONNECT_PROTOCOL = "openconnect-ssl"


def gateway_payload(gateway: Gateway) -> dict:
    return {
        "name": gateway.name,
        "address": gateway.address,
        "protocol": gateway.protocol,
        "port": gateway.port,
        "priority": gateway.priority,
        "notes": gateway.notes,
    }


def gateways_for_protocol(gateways: Iterable[Gateway], protocol: str) -> list[dict]:
    return [gateway_payload(gateway) for gateway in gateways if gateway.protocol == protocol]


def build_connection_config(
    account: dict,
    gateways: Iterable[Gateway],
    vpn_shared_psk: str,
    ca_certificate_url: str,
) -> dict:
    gateway_list = tuple(gateways)
    return {
        "account": {
            "username": account["username"],
            "status": account["status"],
            "speed_profile": account["display_name"],
            "max_concurrent_sessions": account["max_concurrent_sessions"],
        },
        "native_l2tp_ipsec": {
            "shared_psk": vpn_shared_psk,
            "gateways": gateways_for_protocol(gateway_list, L2TP_PROTOCOL),
        },
        "uniconnect_ssl": {
            "auth_mode": "username_password",
            "username": account["username"],
            "password": "use the VPN account password configured in the admin portal",
            "ca_certificate_url": ca_certificate_url,
            "gateways": gateways_for_protocol(gateway_list, UNICONNECT_PROTOCOL),
            "android_guide_url": "/guides/android",
        },
    }
