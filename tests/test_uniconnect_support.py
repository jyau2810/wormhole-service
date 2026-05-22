from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
