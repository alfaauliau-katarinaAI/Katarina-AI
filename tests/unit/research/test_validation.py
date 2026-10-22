"""Stage 1 validation tool: determinism, holdout lock, leakage refusal and reporting.

Synthetic trades test the TOOL, never a strategy; nothing here is trading evidence.
"""
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.governance.promotion_gate import file_sha256
from katarina.research import validation as v

UTC = timezone.utc
SPEC = {"name": "pullback-synthetic", "symbol": "XAUUSD.SYNTH", "side": "BUY", "regime": "TREND_UP",
        "playbook": "TREND_PULLBACK", "rules": "synthetic fixture", "parameters": {"rr": 2}}
SPLIT = v.DataSplit(datetime(2026, 1, 5, tzinfo=UTC), datetime(2026, 7, 6, tzinfo=UTC),
                    datetime(2026, 7, 6, tzinfo=UTC), datetime(2027, 1, 4, tzinfo=UTC),
                    gaps=((datetime(2026, 10, 13, tzinfo=UTC), datetime(2026, 10, 26, tzinfo=UTC), "OBSERVER_DOWN"),))
COSTS = v.CostModel(slippage_per_side=0.05, commission_round_trip=0.1)


def trades(start, weeks, per_week=5, pattern=(3.0, -1.0, 2.0, -1.0, 1.5, 2.5, -1.0), prefix="t"):
    rows = []
    for week in range(weeks):
        for k in range(per_week):
            entry = start + timedelta(weeks=week, days=k % 5, hours=8 + k // 5 * 3)
            move = pattern[(week + k) % len(pattern)]
            rows.append(v.Trade(trade_id=f"{prefix}{week}-{k}", side="BUY", entry_at=entry,
                                exit_at=entry + timedelta(hours=2), known_at=entry + timedelta(hours=2),
                                data_until=entry - timedelta(seconds=1), entry_mid=2000.0,
                                exit_mid=2000.0 + move * 10, stop_distance=10.0, spread_entry=0.3,
                                spread_exit=0.3, trend_side="SELL" if k % 2 else "BUY"))
    return rows


class ValidationToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.registry = v.HypothesisRegistry(root / "registry.jsonl")
        self.entry = self.registry.register(SPEC, registered_utc=datetime(2026, 1, 1, tzinfo=UTC))
        self.hid = self.entry["hypothesis_id"]
        dev = trades(datetime(2026, 1, 5, tzinfo=UTC), 24, prefix="d")
        hold = [t for t in trades(datetime(2026, 7, 6, tzinfo=UTC), 12, prefix="h")
                if SPLIT.period(t.entry_at) == "HOLDOUT"]
        self.vault = v.HoldoutVault(dev + hold, SPLIT, self.registry, root / "holdout-openings.jsonl")
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_data_and_code_give_identical_report(self):
        now = datetime(2026, 7, 10, tzinfo=UTC)
        first = v.evaluate_development(self.vault, self.hid, costs=COSTS, as_of=now)
        second = v.evaluate_development(self.vault, self.hid, costs=COSTS, as_of=now)
        self.assertEqual(first, second)
        self.assertEqual(first["report_sha256"], second["report_sha256"])

    def test_development_never_contains_holdout_trades(self):
        self.assertTrue(all(SPLIT.period(t.entry_at) == "DEVELOPMENT" for t in self.vault.development()))
        report = v.evaluate_development(self.vault, self.hid, costs=COSTS, as_of=datetime(2026, 7, 10, tzinfo=UTC))
        self.assertEqual(report["statistics"]["trades"], len(self.vault.development()))
        self.assertEqual(self.vault.openings(), [])

    def test_holdout_requires_recorded_opening_and_opens_once(self):
        with self.assertRaises(v.ValidationError):
            self.vault.open(self.hid, opened_by="owner", now=datetime(2026, 12, 1, tzinfo=UTC), reason="early")
        with self.assertRaises(v.ValidationError):
            self.vault.open("0" * 64, opened_by="owner", now=datetime(2027, 1, 5, tzinfo=UTC), reason="x")
        with self.assertRaises(v.ValidationError):
            v._build_report(v.Evaluation(self.hid, "HOLDOUT", SPLIT, COSTS), [], self.registry,
                            as_of=datetime(2027, 1, 5, tzinfo=UTC))
        self.assertEqual(self.vault.openings(), [])
        report = v.evaluate_holdout(self.vault, self.hid, costs=COSTS, opened_by="owner", reason="final",
                                    now=datetime(2027, 1, 5, tzinfo=UTC))
        self.assertEqual(len(self.vault.openings()), 1)
        self.assertEqual(report["holdout_opening_sha256"], self.vault.openings()[0]["entry_sha256"])
        with self.assertRaises(v.HoldoutAlreadyOpened):
            v.evaluate_holdout(self.vault, self.hid, costs=COSTS, opened_by="owner", reason="again",
                               now=datetime(2027, 1, 6, tzinfo=UTC))

    def test_future_information_is_rejected(self):
        dev = list(self.vault.development())
        leaked = replace(dev[0], trade_id="leak", data_until=dev[0].entry_at + timedelta(minutes=5),
                         entry_at=dev[0].entry_at - timedelta(days=2), exit_at=dev[0].entry_at - timedelta(days=2,
                         hours=-1), known_at=dev[0].entry_at - timedelta(days=2, hours=-1))
        early = replace(dev[1], trade_id="early-known", known_at=dev[1].exit_at - timedelta(minutes=1))
        crossing = replace(dev[-1], trade_id="cross", entry_at=datetime(2026, 7, 5, 22, tzinfo=UTC),
                           data_until=datetime(2026, 7, 5, 21, tzinfo=UTC),
                           exit_at=datetime(2026, 7, 6, 1, tzinfo=UTC), known_at=datetime(2026, 7, 6, 1, tzinfo=UTC))
        accepted, rejected = v.guard_trades([leaked, early, crossing], SPLIT, "DEVELOPMENT")
        self.assertEqual(accepted, [])
        self.assertEqual(dict(rejected), {"leak": "LOOKAHEAD_DATA_AFTER_ENTRY",
                                          "early-known": "OUTCOME_KNOWN_BEFORE_EXIT",
                                          "cross": "CROSSES_PERIOD_END"})

    def test_rejected_trades_fail_the_report(self):
        dev = list(self.vault.development())
        bad = replace(dev[0], trade_id="bad", data_until=dev[0].entry_at + timedelta(hours=1))
        vault = v.HoldoutVault(dev[1:] + [bad], SPLIT, self.registry, self.root / "other.jsonl")
        report = v.evaluate_development(vault, self.hid, costs=COSTS, as_of=datetime(2026, 7, 10, tzinfo=UTC))
        self.assertFalse(report["gates"]["no_rejected_trades"])
        self.assertEqual(report["verdict"], "FAIL")

    def test_gap_entries_and_wrong_side_are_rejected(self):
        hold = [t for t in trades(datetime(2026, 10, 13, tzinfo=UTC), 1, prefix="g")]
        _, rejected = v.guard_trades(hold, SPLIT, "HOLDOUT")
        self.assertTrue(all(reason == "ENTRY_IN_GAP" for _, reason in rejected))
        sell = replace(self.vault.development()[0], side="SELL")
        _, rejected = v.guard_trades([sell], SPLIT, "DEVELOPMENT", expected_side="BUY")
        self.assertEqual(rejected[0][1], "SIDE_NOT_REGISTERED")

    def test_net_r_and_baselines(self):
        trade = self.vault.development()[0]
        self.assertAlmostEqual(COSTS.cost_r(trade), (0.15 + 0.15 + 0.1 + 0.1) / 10)
        self.assertAlmostEqual(COSTS.net_r(trade, "SELL"), -COSTS.gross_r(trade) - COSTS.cost_r(trade))
        report = v.evaluate_development(self.vault, self.hid, costs=COSTS, as_of=datetime(2026, 7, 10, tzinfo=UTC))
        base = report["baselines"]
        self.assertEqual(base["no_trade"]["expectancy_r"], 0.0)
        self.assertAlmostEqual(base["random_side_same_timing"]["expected_expectancy_r"], -0.05)
        self.assertIsNotNone(base["trend_rule"]["expectancy_r"])
        for key in ("expectancy_r", "trades"):
            self.assertIn(key, report["statistics"])
        self.assertIn("weekly_block_bootstrap_lower_expectancy_r", report)
        self.assertEqual(report["trial_count"], 1)
        self.assertTrue(report["walk_forward"])

    def test_changed_definition_is_a_new_trial_and_identical_is_not(self):
        self.registry.register(SPEC, registered_utc=datetime(2026, 2, 1, tzinfo=UTC))
        self.assertEqual(self.registry.trial_count(), 1)
        changed = dict(SPEC, parameters={"rr": 3})
        self.assertNotEqual(self.registry.register(changed, registered_utc=datetime(2026, 2, 1, tzinfo=UTC))
                            ["hypothesis_id"], self.hid)
        self.assertEqual(self.registry.trial_count(), 2)
        with self.assertRaises(v.ValidationError):
            self.registry.register(dict(SPEC, side="BOTH"), registered_utc=datetime(2026, 2, 1, tzinfo=UTC))

    def test_more_trials_widen_the_confidence_bound(self):
        dev = self.vault.development()
        values = [COSTS.net_r(t) for t in dev]
        blocks = v.weekly_blocks(dev, values)
        one, _ = v.block_bootstrap_lower(blocks, trials=1, seed="s")
        many, alpha = v.block_bootstrap_lower(blocks, trials=50, seed="s")
        self.assertLess(many, one)
        self.assertAlmostEqual(alpha, 0.001)

    def test_ledger_tampering_is_detected(self):
        path = self.root / "registry.jsonl"
        entry = json.loads(path.read_text())
        entry["spec"]["parameters"]["rr"] = 9
        path.write_text(json.dumps(entry) + "\n")
        with self.assertRaises(v.ValidationError):
            self.registry.trial_count()

    def test_holdout_with_too_few_trades_is_pending_not_fail(self):
        report = v.evaluate_holdout(self.vault, self.hid, costs=COSTS, opened_by="owner", reason="final",
                                    now=datetime(2027, 1, 5, tzinfo=UTC))
        self.assertLess(report["statistics"]["trades"], v.PROMOTION_MIN_TRADES)
        self.assertEqual(report["verdict"], "PENDING_INSUFFICIENT_SAMPLE")
        self.assertFalse(report["live_execution_authorized"])

    def test_strong_synthetic_edge_passes_and_report_hash_feeds_promotion_gate(self):
        hold = trades(datetime(2026, 7, 6, tzinfo=UTC), 26, per_week=10, prefix="H")
        hold = [t for t in hold if SPLIT.period(t.entry_at) == "HOLDOUT"]
        vault = v.HoldoutVault(hold, SPLIT, self.registry, self.root / "strong.jsonl")
        report = v.evaluate_holdout(vault, self.hid, costs=COSTS, opened_by="owner", reason="final",
                                    now=datetime(2027, 1, 5, tzinfo=UTC))
        self.assertEqual(report["verdict"], "PASS", report["gates"])
        path = self.root / "report.json"
        self.assertEqual(v.write_report(report, path), file_sha256(path))

    def test_split_must_be_ordered(self):
        with self.assertRaises(v.ValidationError):
            v.DataSplit(datetime(2026, 7, 1, tzinfo=UTC), datetime(2026, 8, 1, tzinfo=UTC),
                        datetime(2026, 7, 15, tzinfo=UTC), datetime(2026, 9, 1, tzinfo=UTC))

    def test_missing_or_partial_trend_baseline_cannot_pass(self):
        for missing in (1, len(self.vault.development())):
            with self.subTest(missing=missing):
                rows = list(self.vault.development())
                rows[:missing] = [replace(t, trend_side=None) for t in rows[:missing]]
                vault = v.HoldoutVault(rows, SPLIT, self.registry, self.root / "baseline.jsonl")
                report = v.evaluate_development(vault, self.hid, costs=COSTS,
                                                as_of=datetime(2026, 7, 10, tzinfo=UTC))
                self.assertEqual(report["verdict"], "FAIL")
                self.assertFalse(report["gates"]["all_baselines_available"])

    def test_future_outcomes_cannot_be_used_in_as_of_report(self):
        report = v.evaluate_development(self.vault, self.hid, costs=COSTS,
                                        as_of=datetime(2026, 1, 6, tzinfo=UTC))
        self.assertEqual(report["verdict"], "FAIL")
        self.assertIn("OUTCOME_NOT_YET_KNOWN", {r["reason"] for r in report["rejected_trades"]})

    def test_gap_rows_are_reported_instead_of_silently_discarded(self):
        gap = trades(datetime(2026, 10, 13, tzinfo=UTC), 1)
        vault = v.HoldoutVault(gap, SPLIT, self.registry, self.root / "gap.jsonl")
        report = v.evaluate_holdout(vault, self.hid, costs=COSTS, opened_by="test", reason="synthetic",
                                    now=datetime(2027, 1, 5, tzinfo=UTC))
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(len(report["rejected_trades"]), len(gap))
        self.assertTrue(all(r["reason"] == "ENTRY_IN_GAP" for r in report["rejected_trades"]))

    def test_position_spanning_gap_is_rejected(self):
        row = trades(datetime(2026, 10, 12, tzinfo=UTC), 1)[0]
        row = replace(row, exit_at=datetime(2026, 10, 26, tzinfo=UTC),
                      known_at=datetime(2026, 10, 26, tzinfo=UTC))
        accepted, rejected = v.guard_trades([row], SPLIT, "HOLDOUT")
        self.assertEqual(accepted, [])
        self.assertEqual(rejected, [(row.trade_id, "POSITION_CROSSES_GAP")])

    def test_revised_hypothesis_must_wait_for_disjoint_holdout(self):
        self.vault.open(self.hid, opened_by="test", now=datetime(2027, 1, 5, tzinfo=UTC), reason="fixture")
        new = self.registry.register(dict(SPEC, parameters={"rr": 3}),
                                     registered_utc=datetime(2027, 1, 6, tzinfo=UTC))["hypothesis_id"]
        for split in (SPLIT, replace(SPLIT, holdout_end=datetime(2027, 2, 1, tzinfo=UTC))):
            vault = v.HoldoutVault([], split, self.registry, self.root / "holdout-openings.jsonl")
            with self.assertRaisesRegex(v.ValidationError, "unseen_holdout"):
                vault.open(new, opened_by="test", now=datetime(2027, 2, 2, tzinfo=UTC), reason="reuse")
        self.assertEqual(len(self.vault.openings()), 1)
        fresh = replace(SPLIT, holdout_start=datetime(2027, 2, 1, tzinfo=UTC),
                        holdout_end=datetime(2027, 5, 1, tzinfo=UTC))
        vault = v.HoldoutVault([], fresh, self.registry, self.root / "holdout-openings.jsonl")
        self.assertEqual(vault.open(new, opened_by="test", now=datetime(2027, 5, 2, tzinfo=UTC), reason="new"), ())

    def test_code_mismatch_rejected_before_consuming_holdout(self):
        hid = self.registry.register(dict(SPEC, code_sha256="a" * 64),
                                     registered_utc=datetime(2026, 1, 1, tzinfo=UTC))["hypothesis_id"]
        for digest in (None, "b" * 64, "invalid"):
            with self.assertRaises(v.ValidationError):
                v.evaluate_holdout(self.vault, hid, costs=COSTS, opened_by="test", reason="fixture",
                                   now=datetime(2027, 1, 5, tzinfo=UTC), code_sha256=digest)
        self.assertEqual(self.vault.openings(), [])
        report = v.evaluate_holdout(self.vault, hid, costs=COSTS, opened_by="test", reason="fixture",
                                    now=datetime(2027, 1, 5, tzinfo=UTC), code_sha256="a" * 64)
        self.assertEqual(report["code_sha256"], "a" * 64)

    def test_hypothesis_cannot_be_registered_after_evaluation_time(self):
        with self.assertRaisesRegex(v.ValidationError, "registered_in_future"):
            v.evaluate_development(self.vault, self.hid, costs=COSTS,
                                   as_of=datetime(2025, 12, 31, tzinfo=UTC))

    def test_holdout_loader_runs_only_after_persisted_opening(self):
        calls = []
        def load():
            self.assertEqual(len(vault.openings()), 1)
            calls.append(True)
            return []
        vault = v.HoldoutVault([], SPLIT, self.registry, self.root / "lazy.jsonl", holdout_loader=load)
        v.evaluate_development(vault, self.hid, costs=COSTS, as_of=datetime(2026, 7, 10, tzinfo=UTC))
        with self.assertRaisesRegex(v.ValidationError, "not_finished"):
            vault.open(self.hid, opened_by="test", now=datetime(2026, 12, 1, tzinfo=UTC), reason="early")
        self.assertEqual(calls, [])
        vault.open(self.hid, opened_by="test", now=datetime(2027, 1, 5, tzinfo=UTC), reason="fixture")
        self.assertEqual(calls, [True])
        with self.assertRaises(v.HoldoutAlreadyOpened):
            vault.open(self.hid, opened_by="test", now=datetime(2027, 1, 6, tzinfo=UTC), reason="retry")
        self.assertEqual(calls, [True])


if __name__ == "__main__":
    unittest.main()
