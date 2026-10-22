"""Synthetic tool tests, never evidence of a profitable market filter."""
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.research import validation as v
from katarina.research.market_intelligence import (
    FavorableOutcome, FilterPolicy, MarketContext, decide_filter, evaluate_market_filter,
)

UTC = timezone.utc
START = datetime(2026, 1, 5, tzinfo=UTC)
NOW = datetime(2026, 7, 2, tzinfo=UTC)
SPLIT = v.DataSplit(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 4, 1, tzinfo=UTC),
                    datetime(2026, 4, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC))
POLICY = dict(max_spread_r=0.1, max_cost_to_range=0.2, min_atr_r=0.1, max_atr_r=2.0,
              min_ticks_per_minute=5, max_context_age_seconds=60, utc_hours=[8, 9])
COSTS = v.CostModel(0.01, 0.02)


class MarketIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.registry = v.HypothesisRegistry(self.root / "registry.jsonl")
        self.spec = dict(name="synthetic-market-filter", symbol="XAUUSD.SYNTH", side="BUY",
                         regime="SYNTH", playbook="SYNTH", rules="Fixture only",
                         parameters={"market_filter": POLICY}, data_split_sha256=SPLIT.sha256)
        self.hid = self.registry.register(self.spec, registered_utc=START - timedelta(days=7))["hypothesis_id"]
        self.trades, self.contexts, self.outcomes = [], [], []
        for i in range(12):
            at = START + timedelta(days=i, hours=8)
            trade = v.Trade(str(i), "BUY", at, at + timedelta(hours=1), at + timedelta(hours=1),
                            at - timedelta(seconds=1), 2000, 2005 if i % 3 else 1995,
                            10, 0.1 if i % 2 else 2.0, 0.1 if i % 2 else 2.0,
                            "BUY" if i % 3 else "SELL")
            self.trades.append(trade)
            self.contexts.append(MarketContext(str(i), "XAUUSD.SYNTH", at - timedelta(minutes=10),
                                               at, 10.0, 5.0, 100, "a" * 64))
            self.outcomes.append(FavorableOutcome(str(i), 10.0, trade.exit_at))

    def evaluate(self, **kwargs):
        args = dict(trades=self.trades, contexts=self.contexts, outcomes=self.outcomes,
                    registry=self.registry, hypothesis_id=self.hid, split=SPLIT, costs=COSTS, as_of=NOW)
        args.update(kwargs)
        return evaluate_market_filter(**args)

    def test_comparison_uses_stage1_and_keeps_authority_disabled(self):
        report = self.evaluate()
        self.assertEqual(report["verdict"], "DEVELOPMENT_IMPROVEMENT")
        self.assertEqual(report["comparison"]["filtered"]["trades"], 6)
        self.assertLess(report["comparison"]["filtered"]["cost_to_favorable_move"],
                        report["comparison"]["unfiltered"]["cost_to_favorable_move"])
        for cohort in ("unfiltered", "filtered"):
            self.assertEqual(report["stage1"][cohort]["tool"], "katarina.research.validation")
            self.assertIn("baselines", report["stage1"][cohort])
            self.assertIn("weekly_block_bootstrap_lower_expectancy_r", report["stage1"][cohort])
        for key in ("stage_clearance_granted", "promotion_authorized", "demo_execution_authorized",
                    "live_execution_authorized"):
            self.assertFalse(report[key])
        self.assertFalse((self.root / "holdout-openings.jsonl").exists())
        self.assertTrue(all(d["reasons"] for d in report["decisions"] if d["action"] == "WAIT"))

    def test_deterministic_including_input_order_and_report_hash(self):
        self.assertEqual(self.evaluate(), self.evaluate())
        self.assertEqual(self.evaluate(), self.evaluate(trades=list(reversed(self.trades)),
                         contexts=list(reversed(self.contexts)), outcomes=list(reversed(self.outcomes))))

    def test_future_exit_spread_and_outcome_cannot_change_filter_decisions(self):
        original = self.evaluate()
        changed = self.evaluate(trades=[replace(t, spread_exit=100) for t in self.trades],
                                outcomes=[replace(o, favorable_move_price=200) for o in self.outcomes])
        self.assertEqual(original["decisions"], changed["decisions"])
        self.assertNotEqual(original["input_sha256"], changed["input_sha256"])
        self.assertNotEqual(original["comparison"], changed["comparison"])

    def test_wait_reasons_cover_session_volatility_activity_staleness_and_cost(self):
        context = replace(self.contexts[1], observed_at=self.contexts[1].observed_at - timedelta(minutes=2),
                          atr_price=30, tick_count=0, range_price=0.01)
        policy = FilterPolicy(**dict(POLICY, utc_hours=[9]))
        decision = decide_filter(self.trades[1], context, policy, COSTS)
        self.assertEqual(set(decision["reasons"]), {"WAIT_SESSION", "WAIT_VOLATILITY", "WAIT_LOW_TICK_ACTIVITY",
                                                   "WAIT_STALE_CONTEXT", "WAIT_COST_RANGE"})

    def test_missing_context_yields_wait_and_incomplete_evidence(self):
        report = self.evaluate(contexts=self.contexts[1:])
        self.assertEqual(report["verdict"], "INCOMPLETE_CONTEXT")
        self.assertEqual(report["decisions"][0]["reasons"], ["WAIT_MISSING_CONTEXT"])

    def test_no_data_and_zero_selected_are_not_pass(self):
        self.assertEqual(self.evaluate(trades=[], contexts=[], outcomes=[])["verdict"], "NO_DATA")
        contexts = [replace(c, tick_count=0) for c in self.contexts]
        report = self.evaluate(contexts=contexts)
        self.assertEqual(report["verdict"], "NO_IMPROVEMENT")
        self.assertIsNone(report["comparison"]["filtered"]["cost_to_favorable_move"])

    def test_unchanged_cohort_is_not_an_improvement(self):
        policy = dict(POLICY, max_spread_r=1, max_cost_to_range=1)
        spec = dict(self.spec, parameters={"market_filter": policy})
        hid = self.registry.register(spec, registered_utc=START - timedelta(days=7))["hypothesis_id"]
        report = self.evaluate(hypothesis_id=hid)
        self.assertEqual(report["trial_count"], 2)
        self.assertEqual(report["verdict"], "NO_IMPROVEMENT")

    def test_leakage_cannot_be_hidden_by_a_wait(self):
        rows = list(self.trades)
        rows[0] = replace(rows[0], data_until=rows[0].entry_at + timedelta(seconds=1))
        with self.assertRaisesRegex(v.ValidationError, "LOOKAHEAD"):
            self.evaluate(trades=rows)

    def test_holdout_and_gap_inputs_are_rejected(self):
        shift = timedelta(days=100)
        t = self.trades[0]
        held = replace(t, entry_at=t.entry_at + shift, exit_at=t.exit_at + shift,
                       known_at=t.known_at + shift, data_until=t.data_until + shift)
        with self.assertRaisesRegex(v.ValidationError, "OUTSIDE_PERIOD"):
            self.evaluate(trades=[held])
        gap = replace(SPLIT, gaps=((t.entry_at - timedelta(minutes=2), t.entry_at - timedelta(minutes=1), "TEST"),))
        hid = self.registry.register(dict(self.spec, data_split_sha256=gap.sha256),
                                     registered_utc=START - timedelta(days=7))["hypothesis_id"]
        with self.assertRaisesRegex(v.ValidationError, "context_window"):
            self.evaluate(split=gap, hypothesis_id=hid)

    def test_future_context_and_outcomes_rejected(self):
        contexts = [replace(self.contexts[0], observed_at=self.trades[0].entry_at + timedelta(seconds=1))]
        with self.assertRaisesRegex(v.ValidationError, "context_after_entry"):
            self.evaluate(contexts=contexts + self.contexts[1:])
        for known in (self.trades[0].entry_at, NOW + timedelta(seconds=1)):
            with self.assertRaisesRegex(v.ValidationError, "outcome_not_known"):
                self.evaluate(outcomes=[replace(self.outcomes[0], known_at=known)] + self.outcomes[1:])

    def test_inconsistent_excursion_rejected(self):
        outcomes = list(self.outcomes)
        outcomes[1] = replace(outcomes[1], favorable_move_price=0)
        with self.assertRaisesRegex(v.ValidationError, "smaller_than_exit"):
            self.evaluate(outcomes=outcomes)

    def test_duplicate_misaligned_and_wrong_symbol_evidence_rejected(self):
        for kwargs in (dict(contexts=self.contexts + [self.contexts[0]]),
                       dict(outcomes=self.outcomes[:-1]), dict(trades=self.trades + [self.trades[0]]),
                       dict(contexts=[replace(c, symbol="EURUSD") for c in self.contexts])):
            with self.subTest(kwargs=list(kwargs)), self.assertRaises(v.ValidationError):
                self.evaluate(**kwargs)

    def test_split_and_code_must_match_registration(self):
        with self.assertRaisesRegex(v.ValidationError, "split_mismatch"):
            self.evaluate(split=replace(SPLIT, development_start=START))
        spec = dict(self.spec, code_sha256="b" * 64)
        hid = self.registry.register(spec, registered_utc=START - timedelta(days=7))["hypothesis_id"]
        with self.assertRaisesRegex(v.ValidationError, "code_does_not_match"):
            self.evaluate(hypothesis_id=hid)

    def test_policy_and_measurements_reject_nonfinite_or_invalid_values(self):
        for update in (dict(max_spread_r=float("nan")), dict(min_atr_r=3), dict(utc_hours=[24]),
                       dict(utc_hours=[8, 8]), dict(min_ticks_per_minute=-1)):
            with self.subTest(update=update), self.assertRaises(v.ValidationError):
                FilterPolicy(**dict(POLICY, **update))
        for update in (dict(tick_count=True), dict(range_price=0), dict(source_sha256="")):
            with self.subTest(update=update), self.assertRaises(v.ValidationError):
                replace(self.contexts[0], **update)

    def test_sell_uses_same_cost_filter_and_directional_outcome_validation(self):
        spec = dict(self.spec, side="SELL")
        hid = self.registry.register(spec, registered_utc=START - timedelta(days=7))["hypothesis_id"]
        report = self.evaluate(trades=[replace(t, side="SELL") for t in self.trades], hypothesis_id=hid)
        self.assertEqual(report["decisions"], self.evaluate()["decisions"])

    def test_cli_writes_report_without_opening_holdout(self):
        def encode(value):
            return value.isoformat() if isinstance(value, datetime) else value
        (self.root / "split.json").write_text(json.dumps(SPLIT.as_dict()))
        (self.root / "costs.json").write_text(json.dumps(asdict(COSTS)))
        for name, rows in (("trades", self.trades), ("contexts", self.contexts), ("outcomes", self.outcomes)):
            (self.root / f"{name}.jsonl").write_text("\n".join(json.dumps(asdict(r), default=encode) for r in rows))
        repo = Path(__file__).resolve().parents[3]
        result = subprocess.run([sys.executable, str(repo / "scripts/research/validate_strategy.py"),
                                 "market-filter", "--workspace", str(self.root), "--hypothesis", self.hid,
                                 "--trades", str(self.root / "trades.jsonl"),
                                 "--contexts", str(self.root / "contexts.jsonl"),
                                 "--outcomes", str(self.root / "outcomes.jsonl")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DEVELOPMENT_IMPROVEMENT", result.stdout)
        reports = list((self.root / "reports").glob("market-filter-*.json"))
        self.assertEqual(len(reports), 1)
        self.assertFalse(json.loads(reports[0].read_text())["promotion_authorized"])
        self.assertFalse((self.root / "holdout-openings.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
