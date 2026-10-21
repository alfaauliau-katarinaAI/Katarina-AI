import json
import sqlite3
import unittest
from datetime import datetime, timezone
from katarina.intelligence.demo.forward_outcomes import ForwardOutcomes

START = 1791288000


def observation(offset=0, bid=100, ask=101, **overrides):
    row = dict(symbol="TEST", bid=bid, ask=ask, tick_time=START+offset,
               connected=True, trade_mode=4, market_reasons=[],
               m1={"atr": 2}, context={"ready": False, "reasons": ["news_missing"]},
               research_candidate=False)
    row.update(overrides)
    return dict(as_of_utc=datetime.fromtimestamp(START+offset, timezone.utc).isoformat(),
                symbols=[row])


class ForwardTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.engine = ForwardOutcomes(self.db)

    def tearDown(self):
        self.db.close()

    def result(self, side="BUY"):
        return self.db.execute("""SELECT status,markout_bps,markout_atr,
            midpoint_bps FROM forward_markouts
            WHERE observation_id=1 AND side=? AND horizon=300""", (side,)).fetchone()

    def test_spread_charged_both_directions(self):
        self.engine.process(1, observation())
        self.engine.process(2, observation(300))
        for side in ("BUY", "SELL"):
            status, bps, atr, mid = self.result(side)
            self.assertEqual(status, "OBSERVED")
            self.assertAlmostEqual(bps, -10000/100.5)
            self.assertEqual(atr, -.5)
            self.assertEqual(mid, 0)

    def test_direction_and_entry_atr_are_fixed(self):
        self.engine.process(1, observation())
        self.engine.process(2, observation(300, 102, 103, m1={"atr": 100}))
        self.assertEqual(self.result("BUY")[2], .5)
        self.assertEqual(self.result("SELL")[2], -1.5)

    def test_no_early_exit(self):
        self.engine.process(1, observation())
        self.engine.process(2, observation(299))
        self.assertEqual(self.result()[0], "PENDING")

    def test_pre_horizon_tick_not_used(self):
        self.engine.process(1, observation())
        self.engine.process(2, observation(310, tick_time=START+299))
        self.assertEqual(self.result()[0], "PENDING")

    def test_missing_exit_never_uses_next_session(self):
        self.engine.process(1, observation())
        self.engine.process(2, observation(391))
        self.assertEqual(self.result(), ("MISSING_EXIT", None, None, None))
        self.engine.process(3, observation(86400, 150, 151))
        self.assertEqual(self.result()[0], "MISSING_EXIT")

    def test_future_and_stale_quotes_not_seeded(self):
        for oid, tick in enumerate((START-31, START+1, float("nan")), 1):
            self.engine.process(oid, observation(tick_time=tick))
        self.assertEqual(self.engine.summary()["counts"], {})

    def test_invalid_market_not_seeded(self):
        self.engine.process(1, observation(market_reasons=["stale_bars"]))
        self.assertEqual(self.engine.summary()["counts"], {})

    def test_macro_blocked_context_preserved(self):
        original = observation()
        self.engine.process(1, original)
        original["symbols"][0]["context"]["ready"] = True
        context = json.loads(self.db.execute(
            "SELECT context FROM forward_markouts LIMIT 1").fetchone()[0])
        self.assertFalse(context["context"]["ready"])
        self.assertEqual(self.engine.summary()["counts"], {"PENDING": 6})

    def test_direction_restrictions(self):
        self.engine.process(1, observation(trade_mode=2))
        sides = self.db.execute("SELECT DISTINCT side FROM forward_markouts").fetchall()
        self.assertEqual(sides, [("SELL",)])

    def test_replay_idempotent(self):
        result = observation()
        self.engine.process(1, result)
        self.engine.process(1, result)
        self.assertEqual(self.engine.summary()["counts"], {"PENDING": 6})

    def test_clock_regression_rejected(self):
        self.engine.process(1, observation(10))
        with self.assertRaises(ValueError):
            self.engine.process(2, observation())

    def test_no_quote_after_disconnect(self):
        self.engine.process(1, observation())
        self.engine.process(2, observation(300, connected=False))
        self.assertEqual(self.result()[0], "PENDING")

    def test_horizons_separate_and_no_promotion(self):
        self.engine.process(1, observation())
        summary = self.engine.process(2, observation(300))
        self.assertEqual(summary["counts"], {"PENDING": 10, "OBSERVED": 2})
        self.assertFalse(summary["model_promotion_allowed"])
        self.assertFalse(summary["commission_slippage_included"])

if __name__ == "__main__":
    unittest.main()
