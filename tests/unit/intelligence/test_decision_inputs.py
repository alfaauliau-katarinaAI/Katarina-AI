"""WP9b measured-input decisions are read-only and fail-closed."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from katarina.intelligence.cognition.decision_inputs import (
    DecisionInputs, LEGACY_MODE, MEASURED_MODE, load_decision_inputs,
)
from katarina.intelligence.news.news_intelligence import NewsContext
from katarina.intelligence.operations import observation_ledger as ledger


class DecisionInputsTests(unittest.TestCase):
    def test_config_defaults_legacy_and_rejects_unknown_values(self):
        self.assertEqual(load_decision_inputs(None).mode, LEGACY_MODE)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "inputs.json"
            for payload in (
                {"schema_version": 1, "mode": MEASURED_MODE},
                {"schema_version": 1, "mode": LEGACY_MODE},
            ):
                path.write_text(json.dumps(payload), encoding="utf-8")
                self.assertEqual(load_decision_inputs(path).mode, payload["mode"])
            for payload in (
                {"schema_version": 2, "mode": MEASURED_MODE},
                {"schema_version": True, "mode": MEASURED_MODE},
                {"schema_version": 1, "mode": "live"},
                {"schema_version": 1},
                ["measured_inputs"],
            ):
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_decision_inputs(path)
            path.write_text("{oops", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_decision_inputs(path)
        with self.assertRaises(ValueError):
            load_decision_inputs("/missing/nonexistent/decision-inputs.json")

    def test_health_requires_every_measured_fact(self):
        valid = dict(
            quote_fresh=True, recent=True, trade_mode=4,
            clock_verified=True, previous_ledger_cycle=True,
        )
        self.assertFalse(DecisionInputs(LEGACY_MODE).system_healthy(**valid))
        measured = DecisionInputs(MEASURED_MODE)
        self.assertTrue(measured.system_healthy(**valid))
        for name, bad in (
            ("quote_fresh", False), ("recent", False), ("trade_mode", 0),
            ("clock_verified", False), ("previous_ledger_cycle", False),
        ):
            with self.subTest(name=name):
                self.assertFalse(measured.system_healthy(**{**valid, name: bad}))
        for trade_mode in (1, 2, 4):
            self.assertTrue(measured.system_healthy(**{**valid, "trade_mode": trade_mode}))
        self.assertFalse(measured.system_healthy(**{**valid, "trade_mode": True}))

    def test_no_news_calendar_clear_is_not_fictitious_blackout(self):
        missing = NewsContext(
            ready=False, blackout=True, risk_score=1.0, sentiment=0.0,
            matched_items=0, source_count=0,
            reasons=("no_fresh_relevant_news_context", "calendar_verified_clear"),
        )
        clear = {"ready": True, "blackout": False}
        self.assertIs(DecisionInputs().news_context(missing, clear), missing)
        revised = DecisionInputs(MEASURED_MODE).news_context(missing, clear)
        self.assertFalse(revised.ready)
        self.assertFalse(revised.blackout)
        self.assertEqual(revised.risk_score, 0.0)
        self.assertIn("no_fresh_relevant_news_calendar_clear", revised.reasons)
        self.assertNotIn("no_fresh_relevant_news_context", revised.reasons)
        self.assertEqual(missing.risk_score, 1.0)
        for calendar in ({"ready": False, "blackout": False},
                         {"ready": True, "blackout": True}):
            self.assertIs(DecisionInputs(MEASURED_MODE).news_context(missing, calendar), missing)
        real_article = NewsContext(
            True, True, .9, 0., 1, 1, ("high_impact_news_blackout",),
        )
        self.assertIs(DecisionInputs(MEASURED_MODE).news_context(real_article, clear), real_article)

    def test_record_shadow_uses_unique_mode_key_and_prior_cycle(self):
        now = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
        with closing(sqlite3.connect(":memory:")) as db:
            self.assertFalse(ledger.previous_cycle_recorded(db, before_utc=now))
            cycle = ledger.record_snapshot(
                db, observed_utc=now - timedelta(minutes=1),
                clock_shift_hours=3, cards={"EURUSD": {"action": "WAIT"}},
                quotes={},
            )
            self.assertTrue(ledger.previous_cycle_recorded(db, before_utc=now))
            self.assertFalse(ledger.previous_cycle_recorded(db, before_utc=now - timedelta(minutes=2)))
            ledger.record_decision_shadow(
                db, cycle, symbol="EURUSD", mode=MEASURED_MODE,
                action="WAIT", conditional_side="WAIT",
                blockers=("no_verified_relevant_news",),
            )
            ledger.record_decision_shadow(
                db, cycle, symbol="EURUSD", mode=MEASURED_MODE,
                action="WAIT", conditional_side="BUY", blockers=("still_blocked",),
            )
            rows = db.execute(
                "SELECT mode,conditional_side,blockers_json FROM decision_shadow"
            ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0:2], (MEASURED_MODE, "BUY"))
            self.assertEqual(json.loads(rows[0][2]), ["still_blocked"])
            with self.assertRaises(ValueError):
                ledger.record_decision_shadow(
                    db, cycle, symbol="EURUSD", mode="live",
                    action="WAIT", conditional_side="WAIT", blockers=(),
                )

    def test_alternate_context_is_bounded_without_workers(self):
        measured = DecisionInputs(MEASURED_MODE)
        missing = NewsContext(False, True, 1., 0., 0, 0, ("no_fresh_relevant_news_context",))
        begin = time.monotonic()
        for _ in range(1000):
            measured.news_context(missing, {"ready": True, "blackout": False})
        self.assertLess(time.monotonic() - begin, 2.0)


if __name__ == "__main__":
    unittest.main()
