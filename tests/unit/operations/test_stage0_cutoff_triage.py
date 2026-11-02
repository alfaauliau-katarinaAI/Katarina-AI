"""Research-only tests for independent Stage0 cutoff diagnostic, not promotion code."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

from scripts.ai import diagnose_stage0_cutoff as triage


class TestStage0CutoffTriage(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.dbpath = Path(self.root.name) / "context.sqlite3"
        with sqlite3.connect(self.dbpath) as db:
            db.execute("CREATE TABLE observer_cycles("
                       "observed_utc TEXT, status TEXT, reason TEXT, clock_shift_hours REAL)")
            db.execute("CREATE TABLE broker_tick_days("
                       "symbol TEXT, day TEXT, status TEXT, snapshots_checked INT, "
                       "snapshots_matched INT, reason TEXT)")
            db.execute("CREATE TABLE observer_quotes("
                       "observed_utc TEXT, symbol TEXT, status TEXT, reason TEXT)")
            db.executemany("INSERT INTO observer_cycles VALUES(?,?,?,?)", [
                ("2026-10-27T10:00:00+00:00", "PARTIAL", "OLD_CLOCK", 2),
                ("2026-10-28T17:01:00+00:00", "OK", None, 2),
                ("2026-10-29T10:00:00+00:00", "OK", None, 2),
                ("2026-10-29T11:00:00+00:00", "PARTIAL", "PARTIAL_QUOTE", 2),
                ("2026-10-30T10:00:00+00:00", "OK", None, 2),
                ("2026-10-30T23:55:00+00:00", "OK", None, -1),
            ])
            db.executemany("INSERT INTO observer_quotes VALUES(?,?,?,?)", [
                ("2026-10-27T10:00:00+00:00", "XAUUSD.vx", "FAILED", "OLD_CLOCK"),
                ("2026-10-29T11:00:00+00:00", "XAUUSD.vx", "FAILED", "no_past_broker_bidask_quote"),
                ("2026-10-30T23:55:00+00:00", "NAS100.vx", "FAILED", "MARKET_CLOSED"),
            ])
            db.executemany("INSERT INTO broker_tick_days VALUES(?,?,?,?,?,?)", [
                ("XAUUSD.vx", "2026-10-27", "STORED", 120, 20, None),
                ("XAUUSD.vx", "2026-10-28", "STORED", 15, 15, None),
                ("XAUUSD.vx", "2026-10-29", "STORED", 20, 20, None),
                ("XAUUSD.vx", "2026-10-30", "GAP", 0, 0,
                 "BROKER_SHIFT_CHANGED_DURING_DAY"),
            ])

    def tearDown(self):
        self.root.cleanup()

    def _report(self):
        with sqlite3.connect(self.dbpath.resolve().as_uri() + "?mode=ro", uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            return triage.summarize(db, as_of=datetime(2026, 11, 3, tzinfo=timezone.utc))

    def test_old_mismatch_remains_visible_but_not_current(self):
        report = self._report()
        self.assertEqual(report["session_cycles"], 4)
        self.assertEqual(report["session_ok"], 3)
        self.assertEqual(report["session_failure_reasons"], {"PARTIAL_QUOTE": 1})
        self.assertEqual(report["session_quote_failure_reasons"], [
            {"symbol": "XAUUSD.vx", "reason": "no_past_broker_bidask_quote", "count": 1},
        ])
        self.assertEqual(report["tick_reconciliation_pre_cutoff_or_partial_day_EXCLUDED"]["mismatches"], 100)
        self.assertEqual(report["tick_reconciliation_completed_days_after_cutoff"]["mismatches"], 0)
        self.assertEqual(report["tick_reconciliation_completed_days_after_cutoff"]["checked"], 20)
        self.assertEqual(len(report["broker_tick_days_incomplete_GAP"]), 1)
        self.assertIn("2026-10-29", [x["utc_day"] for x in report["complete_trading_days"]])
        self.assertNotIn("2026-10-28", [x["utc_day"] for x in report["complete_trading_days"]])
        self.assertEqual(report["verdict"], "DIAGNOSTIC_ONLY_NOT_STAGE0_PASS")

    def test_untrusted_outside_session_shift_is_flagged_not_deleted(self):
        report = self._report()
        friday = next(x for x in report["daily"] if x["utc_day"] == "2026-10-30")
        self.assertEqual(friday["in_session_modal_shift_unverified"], 2)
        self.assertEqual(len(friday["out_of_session_shift_conflicts"]), 1)
        self.assertIn("23:55:00", friday["out_of_session_shift_conflicts"][0])

    def test_output_is_readonly_and_does_not_import_metatrader(self):
        before = hashlib.sha256(self.dbpath.read_bytes()).hexdigest()
        output = io.StringIO()
        with redirect_stdout(output):
            exitcode = triage.main([
                "--state-dir", self.root.name,
                "--as-of", "2026-11-03T00:00:00+00:00",
            ])
        self.assertEqual(exitcode, 0)
        self.assertEqual(hashlib.sha256(self.dbpath.read_bytes()).hexdigest(), before)
        self.assertEqual(json.loads(output.getvalue())["live_execution_authorized"], False)
        self.assertNotIn("MetaTrader5", sys.modules)

    def test_naive_time_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "UTC_AWARE_TIME_REQUIRED"):
            triage.summarize(sqlite3.connect(":memory:"), as_of=datetime(2026, 11, 3))

    def test_missing_tables_fail_closed(self):
        with sqlite3.connect(":memory:") as db:
            report = triage.summarize(db, as_of=datetime(2026, 11, 3, tzinfo=timezone.utc))
        self.assertEqual(report["verdict"], "NO_DATA")


if __name__ == "__main__":
    unittest.main()
