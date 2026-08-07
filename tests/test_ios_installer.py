from __future__ import annotations

import plistlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "images" / "admin-portal"))

from app.ios_installer import build_ios_mobileconfig, ios_profile_filename  # noqa: E402
from app.settings import Gateway  # noqa: E402


class IOSInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateways = (
            Gateway("primary", "vpn.example.com", "l2tp-ipsec-psk", 1701, 1),
            Gateway("fallback", "203.0.113.10", "l2tp-ipsec-psk", 1701, 2),
            Gateway("android", "vpn.example.com", "openconnect-ssl", 443, 3),
        )

    def test_mobileconfig_contains_device_scoped_l2tp_credentials_and_gateways(self) -> None:
        payload = build_ios_mobileconfig(
            username="alice",
            password="Secret<&123",
            vpn_shared_psk="shared<&secret",
            gateways=self.gateways,
        )
        profile = plistlib.loads(payload)

        self.assertEqual(profile["PayloadType"], "Configuration")
        self.assertFalse(profile["PayloadRemovalDisallowed"])
        self.assertEqual(len(profile["PayloadContent"]), 2)
        self.assertEqual(
            [item["PPP"]["CommRemoteAddress"] for item in profile["PayloadContent"]],
            ["vpn.example.com", "203.0.113.10"],
        )
        for item in profile["PayloadContent"]:
            self.assertNotIn("PayloadScope", item)
            self.assertEqual(item["PayloadType"], "com.apple.vpn.managed")
            self.assertEqual(item["VPNType"], "L2TP")
            self.assertEqual(item["PPP"]["AuthName"], "alice")
            self.assertEqual(item["PPP"]["AuthPassword"], "Secret<&123")
            self.assertEqual(item["IPSec"]["AuthenticationMethod"], "SharedSecret")
            self.assertEqual(item["IPSec"]["SharedSecret"], b"shared<&secret")
            self.assertEqual(item["IPv4"]["OverridePrimary"], 1)

    def test_mobileconfig_requires_an_l2tp_gateway(self) -> None:
        with self.assertRaisesRegex(ValueError, "no L2TP/IPSec gateway configured"):
            build_ios_mobileconfig(
                username="alice",
                password="secret",
                vpn_shared_psk="shared-secret",
                gateways=(Gateway("android", "vpn.example.com", "openconnect-ssl", 443, 1),),
            )

    def test_profile_filename_is_safe_for_content_disposition(self) -> None:
        self.assertEqual(ios_profile_filename("alice"), "wormhole-alice-ios.mobileconfig")
        self.assertEqual(ios_profile_filename("../alice bob"), "wormhole-alice-bob-ios.mobileconfig")


if __name__ == "__main__":
    unittest.main()
