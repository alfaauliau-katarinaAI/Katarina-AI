"""No-broker tests for causal evolved rule search and promotion barriers."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
from math import sin
import unittest

from katarina.intelligence.lab.autonomous_strategy_discovery import (
    Candle, Genome, Rule, _features, _simulate, discover, validate_bars,
)


def synthetic_bars(n=930):
    start=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp())
    price=2200.
    bars=[]
    for i in range(n):
        opened=price
        change=.32*sin(i*.27)+.16*sin(i*.079)+(
            .09 if (i//28)%2 == 0 else -.09)
        price=opened+change
        extra=.12+.04*abs(sin(i*.33))
        bars.append(Candle(start+3600*(i+1),opened,
                           max(opened,price)+extra,
                           min(opened,price)-extra,price))
    return tuple(bars)


class DiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bars=synthetic_bars()

    def test_rule_creates_distinct_genome_without_llm(self):
        a=Genome("BUY",(Rule("momentum_3",">=",0.5),),1.5,2.,6)
        b=Genome("SELL",(Rule("momentum_3",">=",0.5),),1.5,2.,6)
        self.assertNotEqual(a.fingerprint,b.fingerprint)
        self.assertNotIn("model",a.to_dict())

    def test_evolution_runs_bounded_and_never_authorizes_orders(self):
        out=discover(self.bars,population=12,generations=2,seed=77)
        self.assertGreaterEqual(out["candidate_trials"],12)
        self.assertLessEqual(out["candidate_trials"],24)
        self.assertEqual(out["bars"],len(self.bars))
        self.assertEqual(out["production_action"],"WAIT")
        self.assertFalse(out["broker_fill_prices_verified"])
        self.assertFalse(out["held_out_was_used_in_selection"])
        self.assertFalse(out["model_promotion_permitted"])
        self.assertFalse(out["code_rewrite_permitted"])
        self.assertFalse(out["live_execution_authorized"])
        self.assertEqual(out["orders_sent"],0)
        self.assertIn(out["intrabar_ambiguity"],("STOP_FIRST",))
        for candidate in out["candidate_rules"]:
            self.assertFalse(candidate["can_authorize_live"])
            self.assertIn(candidate["genome"]["side"],("BUY","SELL"))
            self.assertTrue(1<=len(candidate["genome"]["conditions"])<=3)

    def test_same_seed_fully_deterministic(self):
        a=discover(self.bars,population=10,generations=2,seed=9)
        b=discover(self.bars,population=10,generations=2,seed=9)
        self.assertEqual(a,b)

    def test_mutating_holdout_cannot_change_training_selection(self):
        a=discover(self.bars,population=12,generations=2,seed=10)
        boundary=a["holdout_start_index"]
        changed=[]
        for idx,b in enumerate(self.bars):
            if idx < boundary:
                changed.append(b)
            else:
                # Only unseen future data change; never touching training.
                new_close=b.close+2.*sin(idx*.41)
                changed.append(Candle(
                    b.close_at,b.open,max(b.high,new_close)+.1,
                    min(b.low,new_close)-.1,new_close))
        b=discover(tuple(changed),population=12,generations=2,seed=10)
        self.assertEqual(a["candidate_trials"],b["candidate_trials"])
        self.assertEqual(
            [(v["candidate_id"],v["search_fitness_after_penalties"])
             for v in a["candidate_rules"]],
            [(v["candidate_id"],v["search_fitness_after_penalties"])
             for v in b["candidate_rules"]])
        self.assertNotEqual(a["data_sha256"],b["data_sha256"])

    def test_features_do_not_read_future_bars(self):
        previous=_features(self.bars)[99]
        changed=list(self.bars)
        index=101
        b=changed[index]
        changed[index]=Candle(
            b.close_at,b.open,b.high+15,b.low-15,b.close)
        self.assertEqual(previous,_features(tuple(changed))[99])

    def test_both_stop_and_take_profit_hit_returns_stop(self):
        bars=list(self.bars)
        b=bars[25]
        bars[25]=Candle(b.close_at,b.open,b.open+10,b.open-10,b.open)
        genome=Genome("BUY",(Rule("candle_body",">=",0.2),),1.0,1.0,3)
        exit_bar,value=_simulate(tuple(bars),24,genome,.5,
                                 spread_fraction=0.,fee_r=0.)
        self.assertEqual(exit_bar,25)
        self.assertEqual(value,-1.)

    def test_spread_and_commission_stress_not_improve_result(self):
        genome=Genome("SELL",(Rule("momentum_3","<=",-0.5),),1.,1.5,3)
        a=_simulate(self.bars,100,genome,.7,spread_fraction=0.,fee_r=0.)
        b=_simulate(self.bars,100,genome,.7,spread_fraction=.08,fee_r=.12)
        self.assertLessEqual(b[1],a[1]+.000001)

    def test_invalid_and_short_data_fails_closed(self):
        with self.assertRaises(ValueError):
            discover(self.bars[:100])
        with self.assertRaises(ValueError):
            discover(self.bars,population=100)
        with self.assertRaises(ValueError):
            discover(self.bars,fee_r=-.1)
        bad=list(self.bars)
        bad[23]=replace(bad[23],close_at=bad[22].close_at)
        with self.assertRaises(ValueError):
            validate_bars(tuple(bad))
        with self.assertRaises(ValueError):
            Rule("not_a_feature",">=",1.)

    def test_never_overfits_zero_trades_into_alpha(self):
        # Flat-price bars contain no ATR, hence no valid discoveries.
        t=self.bars[0].close_at
        flat=tuple(Candle(t+3600*(i+1),2000.,2000.,2000.,2000.)
                   for i in range(740))
        result=discover(flat,population=8,generations=1)
        self.assertEqual(result["candidate_rules"],[])
        self.assertEqual(result["production_action"],"WAIT")

if __name__=="__main__":
    unittest.main()
