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

    def test_is_us_dst_transitions(self):
        # 2026 US DST: March 8 (2nd Sun) to Nov 1 (1st Sun)
        self.assertFalse(v.is_us_dst(datetime(2026, 3, 8, 6, 59, tzinfo=UTC)))
        self.assertTrue(v.is_us_dst(datetime(2026, 3, 8, 7, 0, tzinfo=UTC)))
        self.assertTrue(v.is_us_dst(datetime(2026, 11, 1, 5, 59, tzinfo=UTC)))
        self.assertFalse(v.is_us_dst(datetime(2026, 11, 1, 6, 0, tzinfo=UTC)))

    def test_calculate_rollover_nights_dst_and_standard_time(self):
        # US DST: July 15 (Wed), rollover is 21:00 UTC
        entry_dst = datetime(2026, 7, 15, 20, 0, tzinfo=UTC)
        exit_dst = datetime(2026, 7, 15, 21, 30, tzinfo=UTC)
        # July 15 is Wednesday -> triple swap = 3 nights
        self.assertEqual(v.calculate_rollover_nights(entry_dst, exit_dst, triple_swap_weekday=2), 3)

        # July 13 (Mon), rollover is 21:00 UTC -> 1 night
        entry_mon = datetime(2026, 7, 13, 20, 0, tzinfo=UTC)
        exit_mon = datetime(2026, 7, 13, 21, 30, tzinfo=UTC)
        self.assertEqual(v.calculate_rollover_nights(entry_mon, exit_mon, triple_swap_weekday=2), 1)

        # Standard time: Dec 14 (Mon), rollover is 22:00 UTC
        # Entry at 20:00, Exit at 21:30 (before 22:00) -> 0 nights
        entry_std = datetime(2026, 12, 14, 20, 0, tzinfo=UTC)
        exit_std_1 = datetime(2026, 12, 14, 21, 30, tzinfo=UTC)
        self.assertEqual(v.calculate_rollover_nights(entry_std, exit_std_1), 0)

        # Entry at 20:00, Exit at 22:30 (after 22:00) -> 1 night
        exit_std_2 = datetime(2026, 12, 14, 22, 30, tzinfo=UTC)
        self.assertEqual(v.calculate_rollover_nights(entry_std, exit_std_2), 1)

    def test_calculate_rollover_nights_weekend_and_triple_swap(self):
        # Fri 20:00 UTC to Sun 20:00 UTC spans Friday rollover (21:00 UTC in July) but no Sat/Sun rollovers
        entry_fri = datetime(2026, 7, 17, 20, 0, tzinfo=UTC)  # Friday
        exit_sun = datetime(2026, 7, 19, 20, 0, tzinfo=UTC)   # Sunday
        self.assertEqual(v.calculate_rollover_nights(entry_fri, exit_sun), 1)

        # Wed 20:00 to Thu 22:00 in July (spans Wed 21:00 triple swap + Thu 21:00 regular swap = 3 + 1 = 4)
        entry_wed = datetime(2026, 7, 15, 20, 0, tzinfo=UTC)
        exit_thu = datetime(2026, 7, 16, 22, 0, tzinfo=UTC)
        self.assertEqual(v.calculate_rollover_nights(entry_wed, exit_thu, triple_swap_weekday=2), 4)

    def test_swap_credit_and_side_handling(self):
        cost_model = v.CostModel(slippage_per_side=0.0, commission_round_trip=0.0,
                                 swap_long_per_night=0.5, swap_short_per_night=0.0)
        # Negative swap values rejected
        with self.assertRaises(v.ValidationError):
            v.CostModel(swap_long_per_night=-0.1)
        with self.assertRaises(v.ValidationError):
            v.CostModel(triple_swap_weekday=7)

        # Wednesday rollover trade
        trade_buy = v.Trade(trade_id="t1", side="BUY",
                            entry_at=datetime(2026, 7, 15, 20, 0, tzinfo=UTC),
                            exit_at=datetime(2026, 7, 15, 22, 0, tzinfo=UTC),
                            known_at=datetime(2026, 7, 15, 22, 0, tzinfo=UTC),
                            data_until=datetime(2026, 7, 15, 19, 59, tzinfo=UTC),
                            entry_mid=2000.0, exit_mid=2010.0, stop_distance=10.0,
                            spread_entry=0.2, spread_exit=0.2)

        # BUY has long swap 0.5 per night * 3 nights = 1.5 price units
        # Cost = (0.1 + 0.1 + 0 + 0 + 1.5) / 10.0 = 0.17 R
        self.assertAlmostEqual(cost_model.cost_r(trade_buy, side="BUY"), 0.17)

        # SELL has short swap 0.0 per night (credit treated as 0) -> 0.0 swap cost
        # Cost = (0.1 + 0.1 + 0 + 0 + 0) / 10.0 = 0.02 R
        self.assertAlmostEqual(cost_model.cost_r(trade_buy, side="SELL"), 0.02)

    def test_backwards_compatibility_and_cost_sensitivity(self):
        # Legacy costs without swap fields
        legacy_costs = v.CostModel(slippage_per_side=0.05, commission_round_trip=0.1)
        self.assertEqual(legacy_costs.swap_long_per_night, 0.0)
        self.assertEqual(legacy_costs.swap_short_per_night, 0.0)
        self.assertEqual(legacy_costs.triple_swap_weekday, 2)

        trade = self.vault.development()[0]
        self.assertAlmostEqual(legacy_costs.cost_r(trade), (0.15 + 0.15 + 0.1 + 0.1) / 10)

        report = v.evaluate_development(self.vault, self.hid, costs=legacy_costs, as_of=datetime(2026, 7, 10, tzinfo=UTC))
        self.assertIn("cost_sensitivity", report)
        cs = report["cost_sensitivity"]
        self.assertIn("net_expectancy_r_1_5x", cs)
        self.assertIn("net_expectancy_r_2_0x", cs)
        self.assertIn("breakeven_cost_multiple", cs)
        self.assertIn("cost_verdict", cs)
        self.assertIn(cs["cost_verdict"], ("NO_GROSS_EDGE", "NOT_ECONOMIC_AFTER_COSTS", "POSITIVE_AFTER_COSTS"))

    def test_cost_verdict_categories(self):
        # 1. NO_GROSS_EDGE (gross <= 0)
        trade_loss = v.Trade(trade_id="l1", side="BUY",
                             entry_at=datetime(2026, 1, 5, 8, 0, tzinfo=UTC),
                             exit_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
                             known_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
                             data_until=datetime(2026, 1, 5, 7, 59, tzinfo=UTC),
                             entry_mid=2000.0, exit_mid=1990.0, stop_distance=10.0,
                             spread_entry=0.1, spread_exit=0.1, trend_side="BUY")
        vault_loss = v.HoldoutVault([trade_loss], SPLIT, self.registry, self.root / "loss.jsonl")
        rep_loss = v.evaluate_development(vault_loss, self.hid, costs=COSTS, as_of=datetime(2026, 7, 10, tzinfo=UTC))
        self.assertEqual(rep_loss["cost_sensitivity"]["cost_verdict"], "NO_GROSS_EDGE")

        # 2. NOT_ECONOMIC_AFTER_COSTS (gross > 0 but net <= 0 due to heavy costs)
        trade_small_win = v.Trade(trade_id="w1", side="BUY",
                                  entry_at=datetime(2026, 1, 5, 8, 0, tzinfo=UTC),
                                  exit_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
                                  known_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
                                  data_until=datetime(2026, 1, 5, 7, 59, tzinfo=UTC),
                                  entry_mid=2000.0, exit_mid=2000.5, stop_distance=10.0,
                                  spread_entry=1.0, spread_exit=1.0, trend_side="BUY")
        heavy_costs = v.CostModel(slippage_per_side=0.2, commission_round_trip=0.2)
        vault_win = v.HoldoutVault([trade_small_win], SPLIT, self.registry, self.root / "win.jsonl")
        rep_ne = v.evaluate_development(vault_win, self.hid, costs=heavy_costs, as_of=datetime(2026, 7, 10, tzinfo=UTC))
        self.assertEqual(rep_ne["cost_sensitivity"]["cost_verdict"], "NOT_ECONOMIC_AFTER_COSTS")

        # 3. POSITIVE_AFTER_COSTS (gross > 0 and net > 0)
        trade_big_win = v.Trade(trade_id="bw1", side="BUY",
                                entry_at=datetime(2026, 1, 5, 8, 0, tzinfo=UTC),
                                exit_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
                                known_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
                                data_until=datetime(2026, 1, 5, 7, 59, tzinfo=UTC),
                                entry_mid=2000.0, exit_mid=2020.0, stop_distance=10.0,
                                spread_entry=0.1, spread_exit=0.1, trend_side="BUY")
        vault_big = v.HoldoutVault([trade_big_win], SPLIT, self.registry, self.root / "big.jsonl")
        rep_pos = v.evaluate_development(vault_big, self.hid, costs=COSTS, as_of=datetime(2026, 7, 10, tzinfo=UTC))
        self.assertEqual(rep_pos["cost_sensitivity"]["cost_verdict"], "POSITIVE_AFTER_COSTS")

    def test_random_side_baseline_expected_cost_with_asymmetric_swap(self):
        cost_model = v.CostModel(slippage_per_side=0.0, commission_round_trip=0.0,
                                 swap_long_per_night=0.5, swap_short_per_night=0.1)
        trade = v.Trade(trade_id="t1", side="BUY",
                        entry_at=datetime(2026, 7, 15, 20, 0, tzinfo=UTC),
                        exit_at=datetime(2026, 7, 15, 22, 0, tzinfo=UTC),
                        known_at=datetime(2026, 7, 15, 22, 0, tzinfo=UTC),
                        data_until=datetime(2026, 7, 15, 19, 59, tzinfo=UTC),
                        entry_mid=2000.0, exit_mid=2010.0, stop_distance=10.0,
                        spread_entry=0.2, spread_exit=0.2, trend_side="BUY")

        # BUY cost_r = (0.1 + 0.1 + 1.5) / 10.0 = 0.17 R
        # SELL cost_r = (0.1 + 0.1 + 0.3) / 10.0 = 0.05 R
        # Average random side cost = (0.17 + 0.05) / 2 = 0.11 R
        base = v.baselines([trade], cost_model, seed="test")
        self.assertEqual(base["random_side_same_timing"]["expected_expectancy_r"], -0.11)


if __name__ == "__main__":
    unittest.main()
