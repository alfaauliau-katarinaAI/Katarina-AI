"""Official BLS Employment Situation release-calendar provenance checks (data-only)."""
from datetime import datetime, timezone
from pathlib import Path
import csv
import unittest

from katarina.research.bar_clock_evidence import _calendar_releases, is_us_dst

CALENDAR = Path(__file__).resolve().parents[3] / "config/research/us_release_calendar.csv"


class OfficialBlsCalendarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CALENDAR.read_text(encoding="utf-8")
        cls.rows = list(csv.DictReader(cls.text.splitlines()))

    def test_exact_source_dates_and_no_synthetic_first_friday(self):
        self.assertEqual(len(self.rows), 33)
        self.assertEqual(len(_calendar_releases(self.text)), 33)
        releases = {row["release_date"]: row["release_utc"] for row in self.rows}
        self.assertNotIn("2025-10-03", releases)  # shutdown: postponed
        self.assertNotIn("2025-11-07", releases)  # October report canceled
        self.assertEqual(releases["2025-11-20"], "2025-11-20T13:30:00+00:00")
        self.assertEqual(releases["2025-12-16"], "2025-12-16T13:30:00+00:00")
        self.assertIn("2026-02-11", releases)  # Wednesday, NOT the usual first Friday
        self.assertIn("2026-07-02", releases)  # Thursday before Independence Day

    def test_0830_eastern_timezone_conversion_across_dst(self):
        for row in self.rows:
            parsed = datetime.fromisoformat(row["release_utc"])
            self.assertEqual(parsed.date().isoformat(), row["release_date"])
            self.assertEqual((parsed.hour, parsed.minute),
                             (12 if is_us_dst(parsed) else 13, 30))
            self.assertEqual(parsed.utcoffset().total_seconds(), 0)
            self.assertTrue(row["source_url"].startswith("https://www.bls.gov/"))

    def test_all_dates_pre_dev_holdout_cutoff_and_unique(self):
        cutoff = datetime.fromisoformat("2026-10-13T00:00:00+00:00")
        times = [datetime.fromisoformat(row["release_utc"]) for row in self.rows]
        self.assertEqual(times, sorted(set(times)))
        self.assertTrue(all(t < cutoff for t in times))


if __name__ == "__main__":
    unittest.main()
