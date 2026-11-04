"""Stage 0 failure breakdown: reproduces the 3 Nov 2026 rollover pattern (synthetic ledger, no broker).

VPS evidence (read-only audit 4 Nov 2026): 192 of 200 counted failures since the 28 Oct cutoff fell
within [-15, +60) min of 17:00 New York. In US winter that is 21:45-23:00 UTC, while the official
legacy session window only excludes 20:45-21:15 UTC. These tests pin that classification without
touching the official verdict.
"""
from datetime import datetime, timedelta, timezone
import sqlite3
import unittest

from katarina.intelligence.operations import data_health, observation_ledger
from katarina.intelligence.operations.stage0_breakdown import breakdown, first_break_window, market_phase

U = timezone.utc


def ledger():
    db = sqlite3.connect(":memory:")
    observation_ledger.setup(db)
    return db


def add_cycle(db, moment, status="OK", reason=None, missing=()):
    cid = "c-" + moment.isoformat()
    db.execute("INSERT INTO observer_cycles(cycle_id, observed_utc, finished_utc, status, reason, clock_shift_hours, "
               "symbols_observed, symbols_with_quote, orders_submitted) VALUES(?,?,?,?,?,?,?,?,0)",
               (cid, moment.isoformat(), moment.isoformat(), status, reason, 2.0, 5, 5 - len(missing)))
    if status in ("OK", "PARTIAL"):
        for symbol in ("EURUSD.vx", "GBPUSD.vx", "USDJPY.vx", "XAUUSD.vx", "NAS100.vx"):
            bad = symbol in missing
            db.execute("INSERT INTO observer_quotes(cycle_id, symbol, observed_utc, tick_epoch, bid, ask, spread, "
                       "quote_age_seconds, status, reason) VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (cid, symbol, moment.isoformat(), None if bad else moment.timestamp(),
                        None if bad else 1.0, None if bad else 1.1, None if bad else .1, None if bad else .5,
                        "FAILED" if bad else "OK", "no_past_broker_bidask_quote" if bad else None))


class Stage0BreakdownTests(unittest.TestCase):
    def test_market_phase_follows_new_york_dst(self):
        self.assertEqual(market_phase(datetime(2026, 11, 3, 22, 20, tzinfo=U)), "DAILY_BREAK_NY17")  # winter
        self.assertEqual(market_phase(datetime(2026, 11, 3, 21, 20, tzinfo=U)), "SESSION")
        self.assertEqual(market_phase(datetime(2026, 10, 29, 21, 20, tzinfo=U)), "DAILY_BREAK_NY17")  # summer
        self.assertEqual(market_phase(datetime(2026, 10, 29, 22, 20, tzinfo=U)), "SESSION")
        self.assertEqual(first_break_window(datetime(2026, 11, 3, tzinfo=U)),
                         (datetime(2026, 11, 3, 21, 45, tzinfo=U), datetime(2026, 11, 3, 23, 0, tzinfo=U)))
        self.assertEqual(first_break_window(datetime(2026, 10, 29, tzinfo=U)),
                         (datetime(2026, 10, 29, 20, 45, tzinfo=U), datetime(2026, 10, 29, 22, 0, tzinfo=U)))

    def test_winter_rollover_failures_are_counted_by_the_official_rule_and_classified(self):
        db = ledger()
        start = datetime(2026, 11, 3, 20, 30, tzinfo=U)
        for minute in range(0, 160):  # 20:30-23:10 UTC, one cycle per minute
            moment = start + timedelta(minutes=minute)
            if datetime(2026, 11, 3, 21, 56, tzinfo=U) <= moment < datetime(2026, 11, 3, 23, 0, tzinfo=U):
                if minute % 3 == 0:  # FX ticks but XAU/NAS are in their daily break
                    add_cycle(db, moment, "PARTIAL", "SOME_SYMBOLS_WITHOUT_QUOTE", ("XAUUSD.vx", "NAS100.vx"))
                else:  # fewer than 3 progressing symbols
                    add_cycle(db, moment, "FAILED", "STALE_QUOTES")
            elif moment == datetime(2026, 11, 3, 21, 29, tzinfo=U):
                add_cycle(db, moment, "FAILED", "STALE_QUOTES")  # thin liquidity before the break
            else:
                add_cycle(db, moment)
        now = datetime(2026, 11, 4, 1, tzinfo=U)
        before = db.execute("SELECT COUNT(*), SUM(status='OK') FROM observer_cycles").fetchone()
        official = data_health.assess(db, now)
        rate = next(c for c in official["criteria"] if c["criterion"] == "cycle_success_rate")
        report = breakdown(db, now)
        # Official counting is unchanged by the breakdown and still counts the winter break.
        self.assertEqual(report["session_views"]["official_stage0_session_open"]["cycles"], rate["cycles"])
        self.assertEqual(report["session_views"]["official_stage0_session_open"]["ok"], rate["ok"])
        self.assertEqual(db.execute("SELECT COUNT(*), SUM(status='OK') FROM observer_cycles").fetchone(), before)
        self.assertEqual(report["failures_by_market_phase"]["SESSION"], 1)  # 21:29 only
        self.assertEqual(report["failures_by_market_phase"]["DAILY_BREAK_NY17"], report["failures"] - 1)
        partial = db.execute("SELECT COUNT(*) FROM observer_cycles WHERE status='PARTIAL'").fetchone()[0]
        self.assertEqual(report["partial_missing_symbol_by_phase"]["DAILY_BREAK_NY17"],
                         {"XAUUSD.vx": partial, "NAS100.vx": partial})
        views = report["session_views"]
        self.assertTrue(views["diagnostic_ny17_-15_+60_daily_break"]["diagnostic_only"])
        self.assertGreater(views["diagnostic_ny17_-15_+60_daily_break"]["rate"],
                           views["official_stage0_session_open"]["rate"])
        self.assertEqual(report["official_verdict_effect"], "NONE")
        self.assertFalse(report["live_execution_authorized"])

    def test_since_and_now_bound_the_breakdown(self):
        db = ledger()
        add_cycle(db, datetime(2026, 11, 2, 14, tzinfo=U), "FAILED", "LOCAL_CONNECT_FAILED")
        add_cycle(db, datetime(2026, 11, 3, 14, tzinfo=U), "FAILED", "LOCAL_CONNECT_FAILED")
        add_cycle(db, datetime(2026, 11, 4, 14, tzinfo=U), "FAILED", "LOCAL_CONNECT_FAILED")
        report = breakdown(db, datetime(2026, 11, 3, 23, tzinfo=U), since=datetime(2026, 11, 3, tzinfo=U))
        self.assertEqual(report["failures"], 1)
        self.assertEqual(report["failures_by_day"], {"2026-11-03": {"LOCAL_CONNECT_FAILED": 1}})
        self.assertEqual(report["failures_by_market_phase"], {"SESSION": 1})
        with self.assertRaises(ValueError):
            breakdown(db, datetime(2026, 11, 3, 23))

    def test_cli_breakdown_is_read_only_and_never_changes_the_verdict(self):
        import contextlib, hashlib, io, json, tempfile
        from pathlib import Path
        from scripts.ai import check_stage0_health
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "context.sqlite3"
            db = sqlite3.connect(path)
            observation_ledger.setup(db)
            add_cycle(db, datetime(2026, 11, 3, 22, 10, tzinfo=U), "FAILED", "STALE_QUOTES")
            add_cycle(db, datetime(2026, 11, 3, 14, 0, tzinfo=U))
            db.commit()
            db.close()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            out = Path(tmp) / "breakdown.json"
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                code = check_stage0_health.main(["--state-dir", tmp, "--breakdown", "--output", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["failures_by_market_phase"], {"DAILY_BREAK_NY17": 1})
            self.assertIn("official_verdict_effect=NONE", printed.getvalue())


if __name__ == "__main__":
    unittest.main()
