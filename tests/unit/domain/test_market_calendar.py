"""katarina.domain.market_calendar: the single US/EU DST source (cleanup C1)."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
import unittest

from katarina.domain.market_calendar import dst_transitions, is_eu_dst, is_us_dst, last_sunday, nth_sunday

UTC = timezone.utc
SRC = Path(__file__).resolve().parents[3] / "src" / "katarina"


class MarketCalendarTests(unittest.TestCase):
    def test_known_transition_dates(self):
        self.assertEqual(nth_sunday(2026, 3, 2), date(2026, 3, 8))
        self.assertEqual(nth_sunday(2026, 11, 1), date(2026, 11, 1))
        self.assertEqual(last_sunday(2026, 3), date(2026, 3, 29))
        self.assertEqual(last_sunday(2026, 10), date(2026, 10, 25))
        self.assertEqual(last_sunday(2026, 12), date(2026, 12, 27))
        self.assertEqual(dst_transitions(2026),
                         [date(2026, 3, 8), date(2026, 3, 29), date(2026, 10, 25), date(2026, 11, 1)])

    def test_us_boundaries_are_half_open_in_utc(self):
        start, end = datetime(2026, 3, 8, 7, tzinfo=UTC), datetime(2026, 11, 1, 6, tzinfo=UTC)
        tick = timedelta(microseconds=1)
        self.assertFalse(is_us_dst(start - tick))
        self.assertTrue(is_us_dst(start))
        self.assertTrue(is_us_dst(end - tick))
        self.assertFalse(is_us_dst(end))

    def test_eu_boundaries_are_half_open_in_utc(self):
        start, end = datetime(2026, 3, 29, 1, tzinfo=UTC), datetime(2026, 10, 25, 1, tzinfo=UTC)
        tick = timedelta(microseconds=1)
        self.assertFalse(is_eu_dst(start - tick))
        self.assertTrue(is_eu_dst(start))
        self.assertTrue(is_eu_dst(end - tick))
        self.assertFalse(is_eu_dst(end))

    def test_non_utc_offsets_are_normalized(self):
        jakarta = timezone(timedelta(hours=7))
        self.assertTrue(is_us_dst(datetime(2026, 3, 8, 14, tzinfo=jakarta)))   # 07:00 UTC
        self.assertFalse(is_us_dst(datetime(2026, 3, 8, 13, 59, tzinfo=jakarta)))

    def test_naive_datetime_is_rejected(self):
        for fn in (is_us_dst, is_eu_dst):
            with self.assertRaisesRegex(ValueError, "^aware_utc_datetime_required$"):
                fn(datetime(2026, 7, 1))

    def test_no_second_dst_implementation_in_source(self):
        """Guard: Sunday/DST rules live only in the domain calendar."""
        offenders = []
        for path in SRC.rglob("*.py"):
            if path.name == "market_calendar.py":
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"^def _?(nth_sunday|last_sunday|is_us_dst|is_eu_dst)\b", text, re.M):
                if "market_calendar" not in text:
                    offenders.append(str(path.relative_to(SRC)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
