from __future__ import annotations

import unittest
from datetime import UTC, datetime

from ssrn_monitor.dates import default_target_date_et, parse_approved_date_to_iso, shift_iso_date


class DatesTest(unittest.TestCase):
    def test_parse_short_format(self) -> None:
        self.assertEqual(parse_approved_date_to_iso("05 Jun 2026"), "2026-06-05")

    def test_parse_long_format(self) -> None:
        self.assertEqual(parse_approved_date_to_iso("June, 05 2026 00:00:00 +0000"), "2026-06-05")

    def test_shift_date(self) -> None:
        self.assertEqual(shift_iso_date("2026-06-01", -1), "2026-05-31")

    def test_default_target_date_et(self) -> None:
        now = datetime(2026, 6, 6, 4, 30, tzinfo=UTC)
        self.assertEqual(default_target_date_et(now), "2026-06-05")


if __name__ == "__main__":
    unittest.main()
