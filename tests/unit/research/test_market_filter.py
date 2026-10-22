"""Stage 2 filter tool: decisions, look-ahead refusal, holdout isolation, reasons and determinism.

Synthetic signals test the TOOL, never a strategy; nothing here is trading evidence.
"""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.research import market_filter as mf
from katarina.research import validation as v

UTC = timezone.utc
BASE = {"name": "pullback-synthetic", "symbol": "XAUUSD.SYNTH", "side": "BUY", "regime": "TREND_UP",
        "playbook": "TREND_PULLBACK", "rules": "synthetic fixture", "parameters": {"rr": 2}}
SPLIT = v.DataSplit(datetime(2026, 1, 5, tzinfo=UTC), datetime(2026, 7, 6, tzinfo=UTC),
                    datetime(2026, 7, 6, tzinfo=UTC), datetime(2027, 1, 4, tzinfo=UTC))
COSTS = v.CostModel(slippage_per_side=0.05, commission_round_trip=0.1)
PARAMS = {"max_spread_to_range": 0.1, "session_hours_utc": [[7, 17]]}


def signals(start, weeks, prefix="s"):
    """Even k: London hours, tight spread, big move. Odd k: Asian hours, wide spread, small move."""
    rows, contexts = [], {}
    for week in range(weeks):
        for k in range(4):
            good = k % 2 == 0
            entry = start + timedelta(weeks=week, days=k, hours=9 if good else 2)
            trade = v.Trade(trade_id=f"{prefix}{week}-{k}", side="BUY", entry_at=entry,
                            exit_at=entry + timedelta(hours=2), known_at=entry + timedelta(hours=2),
                            data_until=entry - timedelta(seconds=1), entry_mid=2000.0,
                            exit_mid=2000.0 + (15 if good else -8), stop_distance=10.0,
                            spread_entry=0.3 if good else 2.5, spread_exit=0.3 if good else 2.5)
            rows.append(trade)
            contexts[trade.trade_id] = mf.MarketContext(
                trade_id=trade.trade_id, context_until=entry - timedelta(seconds=1), typical_range=8.0,
                volatility_ratio=1.0, favorable_move=18.0 if good else 4.0)
    return rows, contexts


class MarketFilterToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.registry = v.HypothesisRegistry(root / "registry.jsonl")
        self.registry.register(BASE, registered_utc=datetime(2026, 1, 1, tzinfo=UTC))
        self.spec = mf.filter_spec(name="london-tight-spread", base_spec=BASE, parameters=PARAMS)
        self.fid = self.registry.register(self.spec, registered_utc=datetime(2026, 1, 2, tzinfo=UTC))["hypothesis_id"]
        dev, self.contexts = signals(datetime(2026, 1, 5, tzinfo=UTC), 20)
        hold, hold_ctx = signals(datetime(2026, 7, 6, tzinfo=UTC), 10, prefix="h")
        self.contexts.update(hold_ctx)
        self.ledger = root / "holdout-openings.jsonl"
        self.vault = v.HoldoutVault(dev + hold, SPLIT, self.registry, self.ledger)
        self.as_of = datetime(2026, 7, 7, tzinfo=UTC)

    def tearDown(self):
        self.tmp.cleanup()

    def test_filter_is_a_registered_trial_bound_to_its_base(self):
        self.assertEqual(self.spec["playbook"], "MARKET_FILTER")
        self.assertEqual(self.spec["parameters"]["base_hypothesis_id"], v.HypothesisRegistry.hypothesis_id(BASE))
        self.assertEqual(self.registry.trial_count(), 2)
        with self.assertRaises(v.ValidationError):
            mf.filter_spec(name="x", base_spec=BASE, parameters={"secret_edge": 1})

    def test_report_improves_cost_ratio_with_reasons_and_is_deterministic(self):
        first = mf.evaluate_filter(self.vault, self.fid, self.contexts, costs=COSTS, as_of=self.as_of)
        again = mf.evaluate_filter(self.vault, self.fid, self.contexts, costs=COSTS, as_of=self.as_of)
        self.assertEqual(first["report_sha256"], again["report_sha256"])
        self.assertEqual(first["verdict"], "PASS")
        self.assertEqual((first["signals"], first["passed"], first["waited"]), (80, 40, 40))
        ratio = first["median_cost_to_favorable_move"]
        self.assertLess(ratio["filtered"], ratio["unfiltered"])
        self.assertTrue(all(w["reasons"] for w in first["waits"]))
        self.assertEqual(first["wait_reasons"], {"OUTSIDE_SESSION": 40, "SPREAD_TOO_WIDE_FOR_RANGE": 40})
        self.assertFalse(first["live_execution_authorized"])

    def test_holdout_is_never_read(self):
        report = mf.evaluate_filter(self.vault, self.fid, self.contexts, costs=COSTS, as_of=self.as_of)
        self.assertFalse(any(w["trade_id"].startswith("h") for w in report["waits"]))
        self.assertEqual(report["signals"], 80)
        self.assertEqual(self.vault.openings(), [])
        self.assertFalse(self.ledger.exists())

    def test_lookahead_context_is_refused_and_fails_the_report(self):
        bad = dict(self.contexts)
        tid = "s0-0"
        trade = next(t for t in self.vault.development() if t.trade_id == tid)
        bad[tid] = mf.MarketContext(trade_id=tid, context_until=trade.entry_at + timedelta(minutes=5),
                                    typical_range=8.0, volatility_ratio=1.0, favorable_move=18.0)
        self.assertEqual(mf.decide(trade, bad[tid], PARAMS), ["LOOKAHEAD_CONTEXT_AFTER_ENTRY"])
        report = mf.evaluate_filter(self.vault, self.fid, bad, costs=COSTS, as_of=self.as_of)
        self.assertFalse(report["gates"]["no_lookahead_context"])
        self.assertEqual(report["verdict"], "FAIL")

    def test_decision_never_reads_the_outcome(self):
        trade = self.vault.development()[0]
        ctx = self.contexts[trade.trade_id]
        flipped = mf.MarketContext(trade_id=ctx.trade_id, context_until=ctx.context_until,
                                   typical_range=ctx.typical_range, volatility_ratio=ctx.volatility_ratio,
                                   favorable_move=-999.0)
        self.assertEqual(mf.decide(trade, ctx, PARAMS), mf.decide(trade, flipped, PARAMS))

    def test_missing_context_and_liquidity_wait_with_reason(self):
        trade = self.vault.development()[0]
        self.assertEqual(mf.decide(trade, None, PARAMS), ["CONTEXT_MISSING"])
        ctx = self.contexts[trade.trade_id]
        self.assertEqual(mf.decide(trade, ctx, {"min_ticks_per_minute": 5}), ["LIQUIDITY_TOO_LOW"])

    def test_filter_that_does_not_help_fails(self):
        loose = mf.filter_spec(name="noop", base_spec=BASE, parameters={"max_spread_to_risk": 10})
        lid = self.registry.register(loose, registered_utc=datetime(2026, 1, 3, tzinfo=UTC))["hypothesis_id"]
        report = mf.evaluate_filter(self.vault, lid, self.contexts, costs=COSTS, as_of=self.as_of)
        self.assertFalse(report["gates"]["cost_to_move_improves"])
        self.assertEqual(report["verdict"], "FAIL")

    def test_base_hypothesis_cannot_be_evaluated_as_filter(self):
        with self.assertRaises(v.ValidationError):
            mf.evaluate_filter(self.vault, v.HypothesisRegistry.hypothesis_id(BASE), self.contexts,
                               costs=COSTS, as_of=self.as_of)


if __name__ == "__main__":
    unittest.main()
