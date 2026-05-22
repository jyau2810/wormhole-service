from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "images" / "admin-portal"))

from app.connection_config import build_connection_config  # noqa: E402
from app.ocserv_policy import render_ocserv_user_policy, validate_ocserv_username  # noqa: E402
from app.radius_sync import radius_check_rows  # noqa: E402
from app.settings import Gateway, load_settings  # noqa: E402


class UniConnectSupportTests(unittest.TestCase):
    def test_gateway_settings_parse_mixed_protocols(self) -> None:
        old_value = os.environ.get("VPN_GATEWAYS")
        try:
            os.environ["VPN_GATEWAYS"] = (
                "["
                '{"name":"android-uniconnect","address":"vpn.example.com","protocol":"openconnect-ssl","port":443,"priority":1},'
                '{"name":"native-l2tp","address":"vpn.example.com","protocol":"l2tp-ipsec-psk","port":1701,"priority":2}'
                "]"
            )
            settings = load_settings()
            self.assertEqual([gateway.protocol for gateway in settings.vpn_gateways], ["openconnect-ssl", "l2tp-ipsec-psk"])
            self.assertEqual(settings.vpn_gateways[0].port, 443)
        finally:
            if old_value is None:
                os.environ.pop("VPN_GATEWAYS", None)
            else:
                os.environ["VPN_GATEWAYS"] = old_value

    def test_connection_config_splits_l2tp_and_uniconnect_gateways(self) -> None:
        payload = build_connection_config(
            account={
                "username": "alice",
                "status": "enabled",
                "display_name": "Standard 10M",
                "max_concurrent_sessions": 2,
            },
            gateways=(
                Gateway("android-uniconnect", "vpn.example.com", "openconnect-ssl", 443, 1, "UniConnect"),
                Gateway("native-l2tp", "vpn.example.com", "l2tp-ipsec-psk", 1701, 2, "Native"),
            ),
            vpn_shared_psk="shared-secret",
            ca_certificate_url="/ca-certificates/root",
        )

        self.assertEqual(payload["native_l2tp_ipsec"]["gateways"][0]["name"], "native-l2tp")
        self.assertEqual(payload["uniconnect_ssl"]["auth_mode"], "username_password")
        self.assertEqual(payload["uniconnect_ssl"]["ca_certificate_url"], "/ca-certificates/root")
        self.assertEqual(payload["uniconnect_ssl"]["gateways"][0]["port"], 443)
        self.assertNotIn("future_ssl_gateway", payload)

    def test_radius_sync_writes_cleartext_password_for_ocserv(self) -> None:
        rows = radius_check_rows(
            username="alice",
            password="Secret123!",
            status="enabled",
            expiration_at=datetime(2099, 1, 1, 0, 0, 0),
            max_concurrent_sessions=2,
        )

        self.assertIn(("alice", "Cleartext-Password", "Secret123!"), rows)
        self.assertTrue(any(row[1] == "NT-Password" and row[2] != "Secret123!" for row in rows))

    def test_ocserv_policy_renders_bandwidth_and_session_limits(self) -> None:
        policy = render_ocserv_user_policy(
            {"max_up_kbps": 2048, "max_down_kbps": 10240},
            max_concurrent_sessions=2,
        )

        self.assertIn("max-same-clients = 2", policy)
        self.assertIn("rx-data-per-sec = 256000", policy)
        self.assertIn("tx-data-per-sec = 1280000", policy)
        self.assertTrue(policy.endswith("\n"))

    def test_ocserv_username_validation_rejects_path_unsafe_values(self) -> None:
        validate_ocserv_username("alice.alpha_01")

        for username in ("../alice", "alice/bob", "alice bob", "", "."):
            with self.subTest(username=username):
                with self.assertRaises(ValueError):
                    validate_ocserv_username(username)

    def test_ocserv_nas_identifier_is_not_written_to_radiusclient_config(self) -> None:
        ocserv_template = (REPO_ROOT / "images" / "ocserv" / "ocserv.conf.template").read_text(encoding="utf-8")
        radiusclient_template = (REPO_ROOT / "images" / "ocserv" / "radiusclient.conf.template").read_text(encoding="utf-8")

        self.assertIn("nas-identifier=__OCSERV_NAS_IDENTIFIER__", ocserv_template)
        self.assertNotIn("nas-identifier __OCSERV_NAS_IDENTIFIER__", radiusclient_template)

    def test_ocserv_image_keeps_lz4_runtime_dependency(self) -> None:
        dockerfile = (REPO_ROOT / "images" / "ocserv" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("lz4-dev", dockerfile)
        self.assertIn("lz4-libs", dockerfile)

    def test_uniconnect_healthcheck_uses_actual_ocserv_process_names(self) -> None:
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("pgrep -x ocserv-main >/dev/null", compose)
        self.assertIn("pgrep -x ocserv-sm >/dev/null", compose)
        self.assertNotIn('test: ["CMD-SHELL", "pgrep -x ocserv >/dev/null"]', compose)

    def test_ocserv_anyconnect_profile_is_enabled_and_rendered(self) -> None:
        ocserv_template = (REPO_ROOT / "images" / "ocserv" / "ocserv.conf.template").read_text(encoding="utf-8")
        dockerfile = (REPO_ROOT / "images" / "ocserv" / "Dockerfile").read_text(encoding="utf-8")
        entrypoint = (REPO_ROOT / "images" / "ocserv" / "entrypoint.sh").read_text(encoding="utf-8")
        profile_template = (REPO_ROOT / "images" / "ocserv" / "profile.xml.template").read_text(encoding="utf-8")
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("user-profile = /etc/ocserv/profile.xml", ocserv_template)
        self.assertIn("COPY profile.xml.template /opt/wormhole/profile.xml.template", dockerfile)
        self.assertIn("cp /opt/wormhole/profile.xml.template /etc/ocserv/profile.xml", entrypoint)
        self.assertIn("__OCSERV_PROFILE_HOST__", entrypoint)
        self.assertIn("<HostAddress>__OCSERV_PROFILE_HOST__</HostAddress>", profile_template)
        self.assertIn("OCSERV_PROFILE_HOST: ${VPN_SERVER_HOST:-vpn.example.com}", compose)


if __name__ == "__main__":
    unittest.main()
