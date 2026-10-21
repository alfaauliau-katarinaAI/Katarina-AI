"""Frozen alpha program regression: synthetic successes are NEVER live approvals."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from katarina.research.alpha_survival import (
    FrozenHypothesis, ClosedOutcome, REGIME_ROUTES, assess,
)

UTC = timezone.utc


def fixtures():
    frozen = FrozenHypothesis(
        symbol="XAUUSD.SYNTHETIC", market_state="TREND_UP",
        side="BUY", playbook="TREND_PULLBACK",
        freeze_at=datetime(2026, 10, 11, tzinfo=UTC),
        holdout_start=datetime(2027, 1, 1, tzinfo=UTC),
        holdout_end=datetime(2027, 7, 1, tzinfo=UTC),
        dataset_sha256="a"*64, preregistered_tests=10,
        independent_holdout_attested=True,
        actual_all_in_cost_attested=True,
        broker_contract_attested=True,
    )
    trade = []
    start = datetime(2027, 1, 4, 10, tzinfo=UTC)
    # Synthetic outcomes are a test of the SCREEN, not backtest evidence.
    for week in range(24):
        for k, gross in enumerate((1., 1., 1., -.6)):
            entry = start + timedelta(weeks=week, hours=4*k)
            trade.append(ClosedOutcome(
                event_id=f"{week}:{k}", entry_at=entry,
                exit_at=entry+timedelta(minutes=30),
                known_at=entry+timedelta(hours=1),
                dataset_sha256="a"*64, net_r_after_reported_costs=gross,
            ))
    return frozen, trade


class AlphaSurvivalTests(unittest.TestCase):
    def test_synthetic_positive_only_passes_shadow_research(self):
        spec, trades = fixtures()
        result = assess(spec, trades, audit_at=datetime(2027, 7, 2, tzinfo=UTC),
                        resamples=256)
        self.assertEqual(result["status"], "PASS_SHADOW_RESEARCH_ONLY", result)
        self.assertTrue(result["shadow_research_qualified"])
        self.assertFalse(result["live_execution_authorized"])
        self.assertFalse(result["alpha_proven_for_live"])
        self.assertEqual(result["checked_outcomes"], 96)
        self.assertGreater(result["measurements"]["weekly_block_bootstrap_lower_mean_r"], 0)

    def test_without_independent_attestation_always_blocked(self):
        spec, rows = fixtures()
        for change in (
            dict(independent_holdout_attested=False),
            dict(actual_all_in_cost_attested=False),
            dict(broker_contract_attested=False),
        ):
            with self.subTest(change=change):
                out = assess(replace(spec, **change), rows,
                             audit_at=datetime(2027, 7, 2, tzinfo=UTC), resamples=128)
                self.assertEqual(out["status"], "BLOCKED_UNATTESTED_REAL_HOLDOUT_AND_COSTS")

    def test_before_holdout_finishes_cannot_pass(self):
        spec, rows = fixtures()
        result = assess(spec, rows, audit_at=datetime(2027, 5, 1, tzinfo=UTC))
        self.assertEqual(result["status"], "BLOCKED_HOLDOUT_NOT_FINISHED")

    def test_duplicate_and_causality_evidence_rejected(self):
        spec, rows = fixtures()
        duplicate = rows + [rows[0]]
        self.assertEqual(assess(spec, duplicate, audit_at=datetime(2027, 7, 2, tzinfo=UTC),
                                resamples=128)["status"],
                         "BLOCKED_CORRUPT_OVERLAPPING_OR_LOOKAHEAD_EVIDENCE")
        cheated = rows.copy()
        cheated[0] = replace(cheated[0], known_at=cheated[0].entry_at)
        self.assertEqual(assess(spec, cheated, audit_at=datetime(2027, 7, 2, tzinfo=UTC),
                                resamples=128)["status"],
                         "BLOCKED_CORRUPT_OVERLAPPING_OR_LOOKAHEAD_EVIDENCE")

    def test_adverse_cost_stress_removes_alpha(self):
        spec, rows = fixtures()
        out = assess(replace(spec, extra_cost_r=1.1), rows,
                     audit_at=datetime(2027, 7, 2, tzinfo=UTC), resamples=128)
        self.assertFalse(out["shadow_research_qualified"])
        self.assertEqual(out["status"], "BLOCKED_STATISTICAL_SCREEN")

    def test_short_history_rejected_even_with_great_returns(self):
        spec, rows = fixtures()
        out = assess(spec, rows[:28], audit_at=datetime(2027, 7, 2, tzinfo=UTC),
                     resamples=128)
        self.assertFalse(out["measurements"]["gates"]["trades"])
        self.assertFalse(out["shadow_research_qualified"])

    def test_all_market_states_have_explicit_routes(self):
        from katarina.intelligence.perception.adaptive_regime import MarketState, Playbook
        self.assertEqual(set(REGIME_ROUTES), {state.value for state in MarketState})
        self.assertTrue(all(playbook in {value.value for value in Playbook}
                            for side, playbook in REGIME_ROUTES.values()))
        self.assertIn("SIDEWAYS", REGIME_ROUTES)
        self.assertIn("BREAKOUT_DOWN", REGIME_ROUTES)
        self.assertIn("REVERSAL_UP", REGIME_ROUTES)
        for state in ("VOLATILITY_SHOCK", "TRANSITION", "UNKNOWN"):
            self.assertEqual(REGIME_ROUTES[state][0], "WAIT")
        spec, rows = fixtures()
        blocked = assess(replace(spec, market_state="TRANSITION", side="BUY",
                                 playbook="OBSERVE"), rows,
                         audit_at=datetime(2027, 7, 2, tzinfo=UTC))
        self.assertFalse(blocked["shadow_research_qualified"])
        self.assertEqual(blocked["status"], "BLOCKED_REGIME_NO_TRADE")

    def test_wrong_direction_and_playbook_rejected(self):
        spec, rows = fixtures()
        a = assess(replace(spec, side="SELL"), rows,
                   audit_at=datetime(2027, 7, 2, tzinfo=UTC))
        b = assess(replace(spec, playbook="RANGE_FADE"), rows,
                   audit_at=datetime(2027, 7, 2, tzinfo=UTC))
        self.assertEqual(a["status"], "BLOCKED_INVALID_REGIME_ROUTE")
        self.assertEqual(b["status"], "BLOCKED_INVALID_REGIME_ROUTE")

    def test_mismatched_source_digest_rejected(self):
        spec, rows = fixtures()
        rows[0] = replace(rows[0], dataset_sha256="b"*64)
        result = assess(spec, rows, audit_at=datetime(2027, 7, 2, tzinfo=UTC))
        self.assertEqual(result["status"], "BLOCKED_CORRUPT_OVERLAPPING_OR_LOOKAHEAD_EVIDENCE")

    def test_no_outcomes_never_passes(self):
        spec, _ = fixtures()
        result = assess(spec, [], audit_at=datetime(2027, 7, 2, tzinfo=UTC))
        self.assertEqual(result["status"], "BLOCKED_NO_OUTCOMES")


if __name__ == "__main__":
    unittest.main()
