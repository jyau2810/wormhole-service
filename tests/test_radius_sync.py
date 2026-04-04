from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "images" / "admin-portal"))

from app.radius_sync import (  # noqa: E402
    effective_radius_expiration,
    format_radius_expiration,
    nt_password_hash,
    to_utc_naive_end_of_day,
)
from app.settings import load_settings  # noqa: E402


class RadiusSyncTests(unittest.TestCase):
    def test_nt_password_hash_matches_known_vector(self) -> None:
        self.assertEqual(nt_password_hash("Password"), "A4F49C406510BDCAB6824EE7C30FD852")

    def test_end_of_day_conversion_uses_timezone(self) -> None:
        utc_value = to_utc_naive_end_of_day("2026-03-18", "Asia/Shanghai")
        self.assertEqual(utc_value, datetime(2026, 3, 18, 15, 59, 59))

    def test_radius_expiration_format(self) -> None:
        formatted = format_radius_expiration(datetime(2026, 3, 18, 15, 59, 59))
        self.assertEqual(formatted, "18 Mar 2026 15:59:59 UTC")

    def test_disabled_account_effective_expiration_is_nowish(self) -> None:
        configured = datetime(2026, 3, 20, 0, 0, 0)
        effective = effective_radius_expiration("disabled", configured)
        self.assertLessEqual(
            effective.replace(tzinfo=timezone.utc),
            datetime.now(timezone.utc),
        )

    def test_gateway_settings_parse_json(self) -> None:
        old_value = os.environ.get("VPN_GATEWAYS")
        try:
            os.environ["VPN_GATEWAYS"] = (
                '[{"name":"telecom","address":"121.33.38.230","protocol":"l2tp-ipsec-psk","port":1701,"priority":1}]'
            )
            settings = load_settings()
            self.assertEqual(settings.vpn_gateways[0].name, "telecom")
            self.assertEqual(settings.vpn_gateways[0].address, "121.33.38.230")
        finally:
            if old_value is None:
                os.environ.pop("VPN_GATEWAYS", None)
            else:
                os.environ["VPN_GATEWAYS"] = old_value


if __name__ == "__main__":
    unittest.main()
