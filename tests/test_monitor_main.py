from __future__ import annotations

import unittest
from datetime import date

from monitor.polling import build_poll_dates


class PollDateTests(unittest.TestCase):
    def test_once_without_date_scans_only_today(self) -> None:
        self.assertEqual(
            build_poll_dates(
                None,
                once=True,
                reference_date=date(2026, 7, 16),
            ),
            ["2026-07-16"],
        )

    def test_explicit_date_is_respected(self) -> None:
        self.assertEqual(
            build_poll_dates(
                "2026-07-01",
                once=False,
                reference_date=date(2026, 7, 16),
            ),
            ["2026-07-01"],
        )

    def test_production_scans_today_and_previous_three_days(self) -> None:
        self.assertEqual(
            build_poll_dates(
                None,
                once=False,
                reference_date=date(2026, 7, 16),
            ),
            [
                "2026-07-16",
                "2026-07-15",
                "2026-07-14",
                "2026-07-13",
            ],
        )


if __name__ == "__main__":
    unittest.main()
