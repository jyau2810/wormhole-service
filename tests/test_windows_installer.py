from __future__ import annotations

import base64
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "images" / "admin-portal"))

from app.settings import Gateway  # noqa: E402
from app.windows_installer import build_windows_installer, windows_installer_filename  # noqa: E402


class WindowsInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateways = (
            Gateway("primary", "vpn.example.com", "l2tp-ipsec-psk", 1701, 1),
            Gateway("fallback", "203.0.113.10", "l2tp-ipsec-psk", 1701, 2),
            Gateway("android", "vpn.example.com", "openconnect-ssl", 443, 3),
        )

    def _decode_powershell(self, payload: bytes) -> str:
        batch = payload.decode("utf-8")
        match = re.search(r"-EncodedCommand ([A-Za-z0-9+/=]+)", batch)
        self.assertIsNotNone(match)
        return base64.b64decode(match.group(1)).decode("utf-16-le")

    def test_installer_creates_all_l2tp_connections_and_connects_primary(self) -> None:
        payload = build_windows_installer(
            username="alice",
            password="Secret<&'123",
            vpn_shared_psk="shared<&'secret",
            gateways=self.gateways,
        )
        powershell = self._decode_powershell(payload)

        self.assertIn("Name = 'Wormhole - primary'; ServerAddress = 'vpn.example.com'", powershell)
        self.assertIn("Name = 'Wormhole - fallback'; ServerAddress = '203.0.113.10'", powershell)
        self.assertNotIn("openconnect-ssl", powershell)
        self.assertIn("$password = 'Secret<&''123'", powershell)
        self.assertIn("$sharedSecret = 'shared<&''secret'", powershell)
        self.assertIn("Add-VpnConnection", powershell)
        self.assertIn("-TunnelType L2tp", powershell)
        self.assertIn("-AuthenticationMethod MSChapv2", powershell)
        self.assertIn("-RememberCredential", powershell)
        self.assertNotIn("-SplitTunneling", powershell)
        self.assertIn("Join-Path $env:SystemRoot 'System32\\rasdial.exe'", powershell)
        self.assertIn("& $rasdial $connection.Name /disconnect", powershell)
        self.assertIn("& $rasdial $primary.Name $username $password", powershell)
        self.assertIn("$primary = $connections[0]", powershell)

    def test_single_gateway_uses_default_connection_name(self) -> None:
        payload = build_windows_installer(
            username="alice",
            password="secret",
            vpn_shared_psk="shared-secret",
            gateways=(self.gateways[0],),
        )
        powershell = self._decode_powershell(payload)
        self.assertIn("Name = 'Wormhole VPN'", powershell)

    def test_installer_requires_an_l2tp_gateway(self) -> None:
        with self.assertRaisesRegex(ValueError, "no L2TP/IPSec gateway configured"):
            build_windows_installer(
                username="alice",
                password="secret",
                vpn_shared_psk="shared-secret",
                gateways=(Gateway("android", "vpn.example.com", "openconnect-ssl", 443, 1),),
            )

    def test_installer_filename_is_safe_for_content_disposition(self) -> None:
        self.assertEqual(windows_installer_filename("alice"), "wormhole-alice-windows.bat")
        self.assertEqual(windows_installer_filename("../alice bob"), "wormhole-alice-bob-windows.bat")


if __name__ == "__main__":
    unittest.main()
