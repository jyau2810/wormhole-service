from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "images" / "admin-portal"))

from app.radius_sync import (  # noqa: E402
    effective_radius_expiration,
    format_radius_expiration,
    hash_vpn_password,
    next_available_slot,
    to_utc_naive_end_of_day,
)


class RadiusSyncTests(unittest.TestCase):
    def test_hash_vpn_password_uses_sha512_crypt(self) -> None:
        hashed = hash_vpn_password("secret-password")
        self.assertTrue(hashed.startswith("$6$"))

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
            effective.replace(tzinfo=UTC),
            datetime.now(UTC),
        )

    def test_next_available_slot(self) -> None:
        self.assertEqual(next_available_slot({2}, 2), 1)
        self.assertEqual(next_available_slot({1}, 2), 2)
        self.assertIsNone(next_available_slot({1, 2}, 2))


if __name__ == "__main__":
    unittest.main()

