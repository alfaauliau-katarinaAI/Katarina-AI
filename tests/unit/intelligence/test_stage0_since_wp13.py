"""Deterministic test suite for Stage 0 health assessment --since ISO filtering."""
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from katarina.intelligence.operations import data_health
from katarina.intelligence.operations import observation_ledger as ledger


class Stage0SinceWP13Tests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "context.sqlite3"
        self.db = sqlite3.connect(self.db_path)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_since_boundary_validation(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            data_health.assess(self.db, now, since=datetime(2026, 10, 20))

        with self.assertRaises(ValueError):
            data_health.assess(self.db, now, since=now + timedelta(days=1))

    def test_since_filters_prior_cycles_and_quotes(self):
        d1 = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)
        d2 = datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)

        c1 = ledger.record_snapshot(self.db, observed_utc=d1, clock_shift_hours=3, cards={"EURUSD": {}}, quotes={"EURUSD": (1.1, 1.1001, d1.timestamp())})
        ledger.close_cycle(self.db, finished_utc=d1, cycle_id=c1, status="OK")

        c2 = ledger.record_snapshot(self.db, observed_utc=d2, clock_shift_hours=3, cards={"EURUSD": {}}, quotes={"EURUSD": (1.101, 1.1011, d2.timestamp())})
        ledger.close_cycle(self.db, finished_utc=d2, cycle_id=c2, status="OK")

        report_all = data_health.assess(self.db, now)
        self.assertEqual(report_all["cycles_total"], 2)

        since_oct22 = datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)
        report_since = data_health.assess(self.db, now, since=since_oct22)
        self.assertEqual(report_since["cycles_total"], 1)
        self.assertEqual(report_since["first_cycle_utc"], d2.isoformat())

    def test_since_no_data_returns_honest_no_data(self):
        d1 = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)

        c1 = ledger.record_snapshot(self.db, observed_utc=d1, clock_shift_hours=3, cards={"EURUSD": {}}, quotes={"EURUSD": (1.1, 1.1001, d1.timestamp())})
        ledger.close_cycle(self.db, finished_utc=d1, cycle_id=c1, status="OK")

        since_after = datetime(2026, 10, 27, 0, 0, tzinfo=timezone.utc)
        report = data_health.assess(self.db, now, since=since_after)
        self.assertEqual(report["cycles_total"], 0)
        self.assertEqual(report["verdict"], "NO_DATA")

    def test_since_partial_day_cutoff_excluded(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        since_partial = datetime(2026, 10, 25, 14, 30, tzinfo=timezone.utc)

        d1 = datetime(2026, 10, 25, 16, 0, tzinfo=timezone.utc)
        c1 = ledger.record_snapshot(self.db, observed_utc=d1, clock_shift_hours=3, cards={"EURUSD": {}}, quotes={"EURUSD": (1.1, 1.1001, d1.timestamp())})
        ledger.close_cycle(self.db, finished_utc=d1, cycle_id=c1, status="OK")

        report = data_health.assess(self.db, now, since=since_partial)
        self.assertEqual(report["since_utc"], since_partial.isoformat())
        self.assertEqual(report["partial_tick_day_excluded"], "2026-10-25")


if __name__ == "__main__":
    unittest.main()
