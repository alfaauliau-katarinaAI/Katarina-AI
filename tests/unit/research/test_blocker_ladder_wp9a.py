"""WP9a Stage 0–2: synthetic blocker diagnostics; never permit orders.

Tests are RED before the read-only ladder implementation exists.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from katarina.research.blocker_ladder import (
    analyze_blockers, read_blocker_ladder,
)
from katarina.research.validation import ValidationError

STAMP = "2026-10-23T00:00:00+00:00"
A = "system_unhealthy"
B = "insufficient_verified_forward_experience"
C = "no_confirmed_closed_candle_entry"
M = "stale_quote"
X = "unrecognized_test_blocker"


def seed(db):
    db.execute("""CREATE TABLE contextual_decisions(
        symbol TEXT NOT NULL, method TEXT NOT NULL, observed_utc TEXT NOT NULL,
        blockers_json TEXT NOT NULL)""")
    for symbol, blockers in (
        ("EURUSD.vx", [A]),
        ("EURUSD.vx", [A, B]),
        ("EURUSD.vx", [A, B, C]),
        ("EURUSD.vx", [A, B, C, M]),
        ("EURUSD.vx", [X]),
        ("GBPUSD.vx", [M]),
        ("GBPUSD.vx", []),
    ):
        db.execute("INSERT INTO contextual_decisions VALUES(?,?,?,?)",
                   (symbol, "TREND_EXPANSION_V9", STAMP,
                    json.dumps(blockers)))
    db.commit()


class BlockerLadderTests(unittest.TestCase):
    def test_cumulative_ladder_and_unknown_never_removed(self):
        with closing(sqlite3.connect(":memory:")) as db:
            seed(db)
            result = analyze_blockers(db)
        total = result["total"]
        self.assertEqual(total["cards"], 7)
        self.assertEqual(total["blocker_frequency"][A], 4)
        self.assertEqual(total["blocker_frequency"][X], 1)
        self.assertEqual(total["unknown_blockers"], {X: 1})
        self.assertEqual(total["only_blocked_by"]["A"], 1)
        self.assertEqual(total["only_blocked_by"]["A+B"], 2)
        self.assertEqual(total["only_blocked_by"]["A+B+C"], 3)
        self.assertEqual(total["ladder"]["baseline"]["remaining_blocked"], 6)
        self.assertEqual(total["ladder"]["fix_A"]["remaining_blocked"], 5)
        self.assertEqual(total["ladder"]["fix_A_B"]["remaining_blocked"], 4)
        self.assertEqual(total["ladder"]["fix_A_B_C"]["remaining_blocked"], 3)
        self.assertEqual(total["ladder"]["fix_A_B_C"]["remaining_by_class"],
                         {"M": 2, "UNKNOWN": 1})
        self.assertEqual(total["classes"]["M"], 2)
        self.assertEqual(result["by_symbol"]["EURUSD.vx"]["cards"], 5)
        self.assertEqual(result["by_symbol"]["GBPUSD.vx"]["cards"], 2)
        self.assertEqual(len(total["top_combinations"]), 7)
        self.assertFalse(result["live_execution_authorized"])
        self.assertIn("diagnostic_only", result["purpose"])

    def test_report_deterministic_after_reverse_insertions(self):
        with closing(sqlite3.connect(":memory:")) as db:
            seed(db)
            first = analyze_blockers(db)
            rows = db.execute("SELECT * FROM contextual_decisions").fetchall()
            db.execute("DELETE FROM contextual_decisions")
            db.executemany("INSERT INTO contextual_decisions VALUES(?,?,?,?)",
                           list(reversed(rows)))
            second = analyze_blockers(db)
        self.assertEqual(first, second)
        self.assertEqual(len(first["report_sha256"]), 64)
        top = first["total"]["top_combinations"]
        self.assertEqual(top[0]["count"], 1)
        self.assertEqual(top[0]["blockers"], [])

    def test_since_utc_filters_and_rejects_naive_dates(self):
        with closing(sqlite3.connect(":memory:")) as db:
            seed(db)
            db.execute("INSERT INTO contextual_decisions VALUES(?,?,?,?)",
                       ("EURUSD.vx", "TREND", "2026-10-22T23:59:59Z",
                        json.dumps([A])))
            filtered = analyze_blockers(db, since="2026-10-23T00:00:00Z")
            self.assertEqual(filtered["total"]["cards"], 7)
            with self.assertRaises(ValidationError):
                analyze_blockers(db, since="2026-10-23T00:00:00")
        self.assertEqual(filtered["since_utc"], STAMP)

    def test_unknown_and_duplicate_reason_are_not_discarded(self):
        with closing(sqlite3.connect(":memory:")) as db:
            seed(db)
            db.execute("INSERT INTO contextual_decisions VALUES(?,?,?,?)",
                       ("AUDUSD.vx", "X", STAMP, json.dumps([X, X])))
            report = analyze_blockers(db)
            self.assertEqual(report["total"]["unknown_blockers"][X], 2)
            self.assertEqual(report["by_symbol"]["AUDUSD.vx"]["blocker_frequency"][X], 1)
            self.assertEqual(report["total"]["ladder"]["fix_A_B_C"]["remaining_blocked"], 4)

    def test_bad_json_or_unknown_schema_fails_closed(self):
        with closing(sqlite3.connect(":memory:")) as db:
            seed(db)
            db.execute("INSERT INTO contextual_decisions VALUES(?,?,?,?)",
                       ("AUDUSD.vx", "X", STAMP, '{"invalid":1}'))
            with self.assertRaisesRegex(ValidationError, "invalid_blockers_json"):
                analyze_blockers(db)
        with closing(sqlite3.connect(":memory:")) as db:
            with self.assertRaisesRegex(ValidationError, "contextual_decisions_unavailable"):
                analyze_blockers(db)

    def test_database_is_read_only_even_with_existing_wal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with closing(sqlite3.connect(root / "context.sqlite3")) as db:
                seed(db)
            before = hashlib.sha256((root / "context.sqlite3").read_bytes()).hexdigest()
            first = read_blocker_ladder(root)
            second = read_blocker_ladder(root)
            after = hashlib.sha256((root / "context.sqlite3").read_bytes()).hexdigest()
            self.assertEqual(first, second)
            self.assertEqual(before, after)
            self.assertEqual(first["total"]["cards"], 7)

    def test_empty_table_fails_neutral_without_invented_metrics(self):
        with closing(sqlite3.connect(":memory:")) as db:
            seed(db)
            db.execute("DELETE FROM contextual_decisions")
            result = analyze_blockers(db)
        self.assertEqual(result["total"]["cards"], 0)
        self.assertEqual(result["total"]["top_combinations"], [])
        self.assertEqual(result["total"]["ladder"]["fix_A_B_C"]["remaining_blocked"], 0)


if __name__ == "__main__":
    unittest.main()
