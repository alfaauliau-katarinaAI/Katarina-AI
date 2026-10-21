"""Only synthetic/isolated context checks: NO LIVE TRADING."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from katarina.intelligence.lab.regime_research_router import (
    ObservedMarketContext, select_shadow_context,
)


def gold_context():
    now = datetime(2026, 10, 12, 6, 5, tzinfo=timezone.utc)
    return ObservedMarketContext(
        symbol="XAUUSD.vx",
        now_utc=now,
        latest_closed_m5_utc=now - timedelta(minutes=5),
        market_open=True,
        quote_age_seconds=2,
        h1_adx_closed=27,
        vwap_reclaim_side=1,
        news_cleared=True,
        broker_costs_verified=True,
        estimated_total_cost_r=0.04,
        active_portfolio_positions=0,
    )


class TestRegimeResearchRouter(unittest.TestCase):
    def test_matching_gold_context_remains_broker_no_trade(self):
        d = select_shadow_context(gold_context())
        self.assertEqual(d.broker_action, "NO_TRADE")
        self.assertFalse(d.live_authorized)
        self.assertEqual(d.shadow_side, "BUY")
        self.assertIn("XAUUSD", d.shadow_candidate)
        self.assertEqual(d.risk_fraction_for_paper_model, 0.005)

    def test_jpn_low_adx_session(self):
        t = datetime(2026, 10, 12, 12, 10, tzinfo=timezone.utc)
        d = select_shadow_context(ObservedMarketContext(
            symbol="JPN225.vx", now_utc=t,
            latest_closed_m5_utc=t-timedelta(minutes=5),
            market_open=True,quote_age_seconds=2,
            h1_adx_closed=18, donchian24_breakout_side=-1,
            news_cleared=True,broker_costs_verified=True,
            estimated_total_cost_r=0.09,active_portfolio_positions=0,
        ))
        self.assertEqual(d.shadow_side, "SELL")
        self.assertEqual(d.broker_action, "NO_TRADE")
        self.assertFalse(d.live_authorized)

    def test_unknown_or_unverified_inputs_fail_closed(self):
        x = gold_context()
        variants=[
            replace(x, source_is_replay_or_paper=False),
            replace(x, news_cleared=False),
            replace(x, broker_costs_verified=False),
            replace(x, quote_age_seconds=120),
            replace(x, estimated_total_cost_r=0.11),
            replace(x, active_portfolio_positions=None),
            replace(x, active_portfolio_positions=1),
            replace(x, now_utc=datetime(2026,10,12,10,0,tzinfo=timezone.utc),
                    latest_closed_m5_utc=datetime(2026,10,12,9,55,tzinfo=timezone.utc)),
            replace(x, h1_adx_closed=16),
            replace(x, vwap_reclaim_side=0),
            replace(x, latest_closed_m5_utc=x.now_utc + timedelta(seconds=1)),
            replace(x, symbol="BTCUSD.vx"),
        ]
        for v in variants:
            with self.subTest(v=v):
                result=select_shadow_context(v)
                self.assertEqual(result.broker_action,"NO_TRADE")
                self.assertIsNone(result.shadow_candidate)
                self.assertFalse(result.live_authorized)


if __name__ == "__main__":
    unittest.main()
