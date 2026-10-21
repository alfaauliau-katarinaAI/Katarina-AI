import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from katarina.intelligence.shadow.strategy_evidence import (
    ClosedStrategyTrade, ForwardStrategyEvidenceGate,
)

UTC = timezone.utc
FROZEN = datetime(2026, 5, 31, tzinfo=UTC)
NOW = datetime(2026, 10, 11, tzinfo=UTC)


def outcomes(*, cost_verified=True, source="PAPER", symbol="XAUUSD"):
    # 60 genuinely NEW sequential closes in four separate calendar months.
    # Three positive outcomes for each loss, moderate week-level variance.
    first = datetime(2026, 6, 1, tzinfo=UTC)
    return [
        ClosedStrategyTrade(
            trade_id=f"event-{i}", symbol=symbol, strategy_id="GOLD_OR",
            closed_at_utc=first + timedelta(days=2*i),
            net_r=1.1 if i % 4 != 3 else -.35,
            provenance=source, costs_verified=cost_verified,
        )
        for i in range(60)
    ]


class ForwardStrategyEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.gate = ForwardStrategyEvidenceGate(bootstrap_draws=300)

    def decision(self, events=None, **kwargs):
        return self.gate.assess(
            symbol="XAUUSD", strategy_id="GOLD_OR",
            frozen_at_utc=FROZEN, as_of_utc=NOW,
            trades=outcomes() if events is None else events, **kwargs,
        )

    def test_good_verified_forward_paper_trades_are_eligible_for_risk_review_only(self):
        v = self.decision()
        self.assertTrue(v.eligible_for_risk_review)
        self.assertEqual(v.reason, "forward_paper_evidence_for_risk_review_only")
        self.assertEqual(v.forward_trades, 60)
        self.assertGreater(v.forward_mean_r, 0)
        self.assertGreater(v.lower_95pct_mean_r, 0)
        self.assertLessEqual(v.risk_multiplier, .75)
        self.assertGreater(v.risk_multiplier, 0)
        self.assertFalse(v.live_authorized)

    def test_unknown_costs_or_historical_replay_cannot_unlock_the_gate(self):
        for events in (outcomes(cost_verified=False),
                       outcomes(source="HISTORICAL")):
            with self.subTest(source=events[0].provenance):
                v = self.decision(events)
                self.assertFalse(v.eligible_for_risk_review)
                self.assertEqual(v.risk_multiplier, 0)
                self.assertEqual(v.reason, "unverified_forward_provenance_or_costs")

    def test_previous_backtest_not_forward(self):
        events = [
            replace(event, closed_at_utc=event.closed_at_utc-timedelta(days=365))
            for event in outcomes()
        ]
        v = self.decision(events)
        self.assertEqual(v.reason, "insufficient_forward_trades")
        self.assertFalse(v.eligible_for_risk_review)

    def test_future_timestamp_must_fail_closed(self):
        events = outcomes()
        events[-1] = replace(events[-1],
                             closed_at_utc=datetime(2026, 12, 1, tzinfo=UTC))
        self.assertEqual(self.decision(events).reason, "future_trade_leakage")

    def test_duplicate_id_mismatched_symbol_and_nonfinite_return_rejected(self):
        events = outcomes()
        for mutated in (
            events+[events[0]],
            events[:-1]+[replace(events[-1], symbol="XAUEUR")],
            events[:-1]+[replace(events[-1], net_r=float("nan"))],
        ):
            self.assertEqual(self.decision(mutated).reason,
                             "invalid_duplicate_or_mismatched_trade")

    def test_weak_results_do_not_unlock(self):
        bad = [replace(t, net_r=(.1 if i % 4 != 3 else -1.))
               for i, t in enumerate(outcomes())]
        v = self.decision(bad)
        self.assertEqual(v.reason, "poor_forward_expectancy_or_drawdown")
        self.assertEqual(v.risk_multiplier, 0)

    def test_insufficient_time_coverage_does_not_unlock_even_with_high_R(self):
        first = datetime(2026, 10, 1, tzinfo=UTC)
        compressed = [
            replace(t, closed_at_utc=first+timedelta(hours=i))
            for i, t in enumerate(outcomes())
        ]
        v = self.decision(compressed)
        self.assertEqual(v.reason, "insufficient_independent_forward_coverage")

    def test_unfrozen_or_naive_metadata_rejected(self):
        self.assertEqual(self.gate.assess(
            symbol="XAUUSD", strategy_id="GOLD_OR", trades=outcomes(),
            frozen_at_utc=NOW, as_of_utc=NOW,
        ).reason, "strategy_not_frozen_before_observation")
        self.assertEqual(self.gate.assess(
            symbol="XAUUSD", strategy_id="GOLD_OR", trades=outcomes(),
            frozen_at_utc=datetime(2026,5,31), as_of_utc=NOW,
        ).reason, "unverified_strategy_identity_or_time")

    def test_empty_trade_history_cannot_unlock(self):
        self.assertEqual(self.decision([]).reason, "no_forward_trades")


if __name__ == "__main__":
    unittest.main()
