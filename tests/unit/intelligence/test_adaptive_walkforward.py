"""Nonleakage, adaptation, risk and missing-data regression tests."""
from __future__ import annotations

import csv
from pathlib import Path
import unittest

from katarina.intelligence.lab.adaptive_strategy_library import (
    ClosedBar, classify_closed_regime, propose_closed_candle_strategies)
from katarina.intelligence.lab.adaptive_walkforward import (
    PaperEvent, SimulatedRiskGuard, StrategyPerformanceMemory,
    replay_walk_forward)


START = 1_760_000_000


def event(i, *, R=1.4, side="BUY", strategy="TREND_PULLBACK",
          symbol="EURUSD.vx", lag=60, score=.90, cost=.06, when=None):
    cut = START + i*300 if when is None else when
    return PaperEvent(symbol, strategy, side, cut, cut+lag,
                      R, score, cost)


class AdaptiveMemoryTests(unittest.TestCase):
    def test_cannot_train_from_same_second_or_future_exit(self):
        e=event(0)
        mem=StrategyPerformanceMemory()
        with self.assertRaisesRegex(ValueError, "outcome_not_yet_known"):
            mem.observe_closed(e, known_at=e.exit_time)
        with self.assertRaisesRegex(ValueError, "outcome_not_yet_known"):
            mem.observe_closed(e, known_at=e.cut)
        mem.observe_closed(e, known_at=e.exit_time+1)
        self.assertEqual(mem.closed_count, 1)

    def test_buy_and_sell_outcomes_never_pool(self):
        mem=StrategyPerformanceMemory()
        for i in range(18):
            v=event(i, R=1.4, side="BUY")
            mem.observe_closed(v,known_at=v.exit_time+1)
        estimate=mem.estimate(event(40,side="SELL"))
        self.assertEqual(estimate.samples,0)
        self.assertFalse(estimate.eligible)

    def test_contextual_memory_fallback(self):
        mem=StrategyPerformanceMemory()
        for i in range(16):
            e=event(i, R=1.3, cost=.02 if i%2 else .15)
            mem.observe_closed(e,known_at=e.exit_time+1)
        newer=event(40,cost=.30)
        estimate=mem.estimate(newer)
        self.assertEqual(estimate.source,"strategy_family_side")
        self.assertEqual(estimate.samples,16)

    def test_replay_starts_wait_and_then_can_adapt(self):
        events=[event(i,R=1.2) for i in range(50)]
        result=replay_walk_forward(events)
        self.assertEqual(result["status"],"HISTORICAL_RESEARCH_ONLY")
        self.assertEqual(result["shadow_outcomes_matured"],50)
        self.assertEqual(result["decisions"][0]["decision"],"WAIT")
        self.assertGreater(result["adaptive"]["trades"],0)
        self.assertEqual(result["orders_sent"],0)

    def test_repeated_losses_result_in_wait(self):
        result=replay_walk_forward([event(i,R=-1.03) for i in range(55)])
        self.assertEqual(result["adaptive"]["trades"],0)
        self.assertEqual(result["adaptive"]["return_pct"],0)
        self.assertLess(result["v6_conditional_benchmark"]["return_pct"],0)

    def test_long_unresolved_trades_do_not_feed_future_memory(self):
        events=[event(i,R=2,lag=200000) for i in range(20)]
        result=replay_walk_forward(events)
        self.assertEqual(result["adaptive"]["trades"],0)
        self.assertTrue(all(x["prior_closed_samples"]==0
                            for x in result["decisions"]))

    def test_current_trade_future_outcome_cannot_change_decision(self):
        earlier=[event(i,R=1.2) for i in range(20)]
        a=event(40,R=5.,strategy="TREND_PULLBACK")
        b=event(40,R=-8.,strategy="ALTERNATE")
        r1=replay_walk_forward(earlier+[a,b])
        a2=event(40,R=-8.,strategy="TREND_PULLBACK")
        b2=event(40,R=5.,strategy="ALTERNATE")
        r2=replay_walk_forward(earlier+[a2,b2])
        x=[x for x in r1["decisions"] if x["cut_broker_time"]==a.cut]
        y=[x for x in r2["decisions"] if x["cut_broker_time"]==a.cut]
        self.assertEqual([(p["strategy_id"],p["decision"]) for p in x],
                         [(p["strategy_id"],p["decision"]) for p in y])

    def test_cost_stress_changes_realized_net_r(self):
        events=[event(i,R=.18) for i in range(40)]
        normal=replay_walk_forward(events,extra_cost_r=0.)
        costly=replay_walk_forward(events,extra_cost_r=.2)
        self.assertLess(costly["v6_conditional_benchmark"]["return_pct"],
                        normal["v6_conditional_benchmark"]["return_pct"])

    def test_same_asset_family_is_not_duplicated(self):
        g=SimulatedRiskGuard(max_open=3)
        reservation,_=g.reserve(event(0,symbol="EURUSD.vx"))
        self.assertIsNotNone(reservation)
        blocked,reason=g.reserve(event(1,symbol="USDJPY.vx"))
        self.assertIsNone(blocked)
        self.assertEqual(reason,"family_exposure_limit")
        g.close(reservation[0],reservation[1],-1.)
        self.assertEqual(len(g.open_families),0)

    def test_risk_limits_hard_bounded(self):
        with self.assertRaises(ValueError):
            SimulatedRiskGuard(risk_fraction=.02)
        with self.assertRaises(ValueError):
            replay_walk_forward([event(0)],extra_cost_r=-.1)

    def test_empty_archive_is_fail_closed(self):
        r=replay_walk_forward([])
        self.assertEqual(r["status"],"NO_ARCHIVED_EVENTS")
        self.assertFalse(r["live_execution_authorized"])

    def test_archive_contains_expected_columns(self):
        root=Path(__file__).resolve().parents[3]
        p=root/"docs/research/outputs/20261012/brain_unified_intraday_v6_trades.csv"
        if not p.exists():
            self.skipTest("archived data not in this checkout")
        with p.open(newline="",encoding="utf-8") as f:
            rows=csv.DictReader(f)
            self.assertTrue({"symbol","cut","exit_time","R","score",
                             "spread_atr"}.issubset(rows.fieldnames))


def bar(i, o, h, l, c):
    return ClosedBar(START+i*300, o, h, l, c)


class ClosedCandleLibraryTests(unittest.TestCase):
    def test_future_bar_refused(self):
        m5=tuple(bar(i,100,101,99,100) for i in range(35))
        h1=tuple(bar(i,100,102,98,100) for i in range(35))
        with self.assertRaisesRegex(ValueError,"noncausal_bar_input"):
            propose_closed_candle_strategies("EURUSD",m5,h1,
                                             now=START+20*300,
                                             spread=.01,point=.001)

    def test_invalid_ohlc_fails(self):
        with self.assertRaises(ValueError):
            ClosedBar(START,10,9,11,10)

    def test_safe_on_insufficient_history(self):
        self.assertEqual(propose_closed_candle_strategies(
            "EURUSD",(),(),now=START,spread=.01,point=.001),())

    def test_spread_veto(self):
        m5=tuple(bar(i,100,101,99,100.3) for i in range(36))
        h1=tuple(bar(i,100,101,99,100.3) for i in range(36))
        self.assertEqual(propose_closed_candle_strategies(
            "EURUSD",m5,h1,now=m5[-1].time,
            spread=10,point=.001),())

    def test_regime_is_deterministic_from_closed_prices(self):
        m5=tuple(bar(i,100,102,99,101) for i in range(40))
        h1=tuple(bar(i,100+i*.9,102+i*.9,99+i*.9,
                     101+i*.9) for i in range(40))
        state=classify_closed_regime(m5,h1,now=h1[-1].time)
        self.assertEqual(state,"TREND_UP")

    def test_library_never_authorizes_trade(self):
        m5=tuple(bar(i,100,102,99,101) for i in range(40))
        h1=tuple(bar(i,100,102,99,101) for i in range(40))
        v=propose_closed_candle_strategies(
            "EURUSD",m5,h1,now=h1[-1].time,spread=.05,point=.01)
        self.assertTrue(all(x.research_only and not x.live_execution_authorized
                            for x in v))


if __name__=="__main__":
    unittest.main()
