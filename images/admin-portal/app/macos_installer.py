from __future__ import annotations

import base64
import io
import plistlib
import re
import stat
import textwrap
import zipfile
from collections.abc import Iterable
from uuid import NAMESPACE_URL, uuid5

from .settings import Gateway

L2TP_PROTOCOL = "l2tp-ipsec-psk"
PROFILE_NAMESPACE = uuid5(NAMESPACE_URL, "https://wormhole.local/macos-vpn-profile")


def _stable_uuid(value: str) -> str:
    return str(uuid5(PROFILE_NAMESPACE, value)).upper()


def _safe_filename_part(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return sanitized or "account"


def build_macos_mobileconfig(
    username: str,
    password: str,
    vpn_shared_psk: str,
    gateways: Iterable[Gateway],
) -> bytes:
    l2tp_gateways = tuple(gateway for gateway in gateways if gateway.protocol == L2TP_PROTOCOL)
    if not l2tp_gateways:
        raise ValueError("no L2TP/IPSec gateway configured")

    profile_key = f"wormhole-macos:{username}"
    profile_identifier = f"com.wormhole.vpn.{uuid5(PROFILE_NAMESPACE, profile_key).hex}"
    multiple_gateways = len(l2tp_gateways) > 1
    payloads = []

    for gateway in l2tp_gateways:
        payload_key = f"{profile_key}:{gateway.name}:{gateway.address}"
        display_name = f"Wormhole - {gateway.name}" if multiple_gateways else "Wormhole VPN"
        payloads.append(
            {
                "PayloadDescription": f"L2TP/IPSec VPN for {username}",
                "PayloadDisplayName": display_name,
                "PayloadIdentifier": f"{profile_identifier}.{uuid5(PROFILE_NAMESPACE, payload_key).hex}",
                "PayloadScope": "User",
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


def build_macos_command(
    username: str,
    password: str,
    vpn_shared_psk: str,
    gateways: Iterable[Gateway],
) -> tuple[str, str]:
    mobileconfig = build_macos_mobileconfig(username, password, vpn_shared_psk, gateways)
    encoded_profile = "\n".join(textwrap.wrap(base64.b64encode(mobileconfig).decode("ascii"), width=76))
    safe_username = _safe_filename_part(username)
    command_filename = f"wormhole-{safe_username}-macos.command"
    mobileconfig_filename = f"wormhole-{safe_username}.mobileconfig"
    script = f"""#!/bin/bash
set -euo pipefail
umask 077

if [[ "$(/usr/bin/uname -s)" != "Darwin" ]]; then
    echo "This installer requires macOS."
    exit 1
fi

temp_root="${{TMPDIR:-/tmp}}"
profile_dir="$(/usr/bin/mktemp -d "${{temp_root%/}}/wormhole-vpn.XXXXXX")"
profile_path="${{profile_dir}}/{mobileconfig_filename}"

cleanup() {{
    /bin/rm -rf "$profile_dir"
}}
trap cleanup EXIT HUP INT TERM

/usr/bin/base64 -D > "$profile_path" <<'WORMHOLE_PROFILE'
{encoded_profile}
WORMHOLE_PROFILE

/usr/bin/open "$profile_path"
echo
echo "The Wormhole VPN profile has opened in System Preferences."
echo "Install the downloaded profile, then return to this window."
read -r -p "Press Return after installation to remove the temporary profile file... " _
"""
    return command_filename, script


def build_macos_installer_archive(
    username: str,
    password: str,
    vpn_shared_psk: str,
    gateways: Iterable[Gateway],
) -> tuple[str, bytes]:
    command_filename, script = build_macos_command(username, password, vpn_shared_psk, gateways)
    archive_filename = f"wormhole-{_safe_filename_part(username)}-macos-installer.zip"
    payload = io.BytesIO()

    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        command_info = zipfile.ZipInfo(command_filename)
        command_info.create_system = 3
        command_info.external_attr = (stat.S_IFREG | 0o755) << 16
        command_info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(command_info, script.encode("utf-8"))

    return archive_filename, payload.getvalue()
