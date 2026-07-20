from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tools.monitor_temperature import (
    TemperatureReading,
    parse_vcgencmd_output,
    read_sysfs_temperature,
    render_reading,
)


class TemperatureToolTests(unittest.TestCase):
    def test_parse_vcgencmd_output(self) -> None:
        self.assertEqual(parse_vcgencmd_output("temp=47.8'C\n"), 47.8)

    def test_read_sysfs_temperature_converts_millicelsius(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text("43125\n", encoding="utf-8")

            celsius, source = read_sysfs_temperature((path,))

        self.assertEqual(celsius, 43.125)
        self.assertIn("sysfs:", source)

    def test_render_reading_includes_sample_minutes_and_temperature(self) -> None:
        reading = TemperatureReading(
            timestamp=datetime(2026, 7, 20, 12, 0, 0),
            celsius=31.2,
            source="demo",
            elapsed_seconds=120,
        )

        rendered = render_reading(2, reading, [reading])

        self.assertIn("muestra 002", rendered)
        self.assertIn("+002.0 min", rendered)
        self.assertIn("31.2 C", rendered)


if __name__ == "__main__":
    unittest.main()
