from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from monitor.system.health import (
    RUNTIME_STATE_KEY,
    _update_total_uptime_seconds,
    read_temperature_celsius,
)


class FakeRuntimeStore:
    def __init__(self):
        self.values: dict[str, str] = {}

    def get_monitor_value(self, key: str) -> str | None:
        return self.values.get(key)

    def set_monitor_value(self, key: str, value: str) -> None:
        self.values[key] = value


class SystemHealthTests(unittest.TestCase):
    def test_read_temperature_celsius_converts_sysfs_millicelsius(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text("43125\n", encoding="utf-8")

            self.assertEqual(read_temperature_celsius((path,)), 43.125)

    def test_total_uptime_tracks_max_seconds_per_boot(self) -> None:
        store = FakeRuntimeStore()

        first_total = _update_total_uptime_seconds(
            store=store,
            boot_id="boot-a",
            uptime_seconds=7200,
        )
        repeated_total = _update_total_uptime_seconds(
            store=store,
            boot_id="boot-a",
            uptime_seconds=3600,
        )
        next_boot_total = _update_total_uptime_seconds(
            store=store,
            boot_id="boot-b",
            uptime_seconds=18000,
        )

        self.assertEqual(first_total, 7200)
        self.assertEqual(repeated_total, 7200)
        self.assertEqual(next_boot_total, 25200)
        self.assertIn("boot-a", store.get_monitor_value(RUNTIME_STATE_KEY))


if __name__ == "__main__":
    unittest.main()
