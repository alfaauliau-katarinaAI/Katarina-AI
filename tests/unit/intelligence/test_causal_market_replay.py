"""Causal replay checks: real MarketDecisionBrain, no future bar leakage."""
import unittest
from datetime import datetime,timedelta,timezone
from dataclasses import replace

from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle
from katarina.intelligence.lab.causal_market_replay import (
    validate_bars,simulate_ohlc_proxy,replay_native_brain,purged_chronological_splits
)
from katarina.intelligence.lab.adaptive_walkforward import PaperEvent

UTC=timezone.utc
END=datetime(2026,10,9,12,tzinfo=UTC)


def series(tf,number,step):
    """Multi-timeframe synthetic candles; never claim broker-derived results."""
    return tuple(SensorCandle(
        END-timedelta(seconds=(number-i-1)*step),
        100+i*.03,100+i*.03+.4,100+i*.03-.4,
        100+i*.03+(.04 if i%2 else -.03),200+i)
        for i in range(number))


class NativeMarketReplayTests(unittest.TestCase):
    def setUp(self):
        self.frames=dict(M5=series("M5",192,300),
                         M15=series("M15",160,900),
                         H1=series("H1",160,3600))

    def test_uses_native_brain_and_no_live_permission(self):
        result=replay_native_brain({"TEST.vx":self.frames},
            max_m5_cuts_per_symbol=150)
        self.assertEqual(result["market_brain_reused"],"MarketDecisionBrain.evaluate")
        self.assertEqual(result["memory_engine_reused"],"adaptive_walkforward.replay_walk_forward")
        self.assertGreater(result["counters"]["evaluated"],0)
        self.assertEqual(result["orders_sent"],0)
        self.assertFalse(result["historical_spread_factual"])
        self.assertFalse(result["independent_unseen_holdout"])
        self.assertFalse(result["live_execution_authorized"])

    def test_poison_future_candle_does_not_change_prior_signal(self):
        first=tuple(self.frames["M5"])
        # Add only future timestamps; a poison price must not rewrite past cards.
        future=[]
        for i in range(8):
            future.append(SensorCandle(END+timedelta(minutes=5*(i+1)),
                100000.,100002.,99998.,100001.))
        original=replay_native_brain({"XAUUSD.vx":self.frames},
                                     max_m5_cuts_per_symbol=190)
        with_future=replay_native_brain({"XAUUSD.vx":{
            **self.frames,"M5":first+tuple(future)}},
            max_m5_cuts_per_symbol=198)
        # Candidates completed before the poisoned tail must be identical.
        before=END-timedelta(hours=2,minutes=30)
        def history(result):
            return [(x["signal_at"],x["method"],x["side"],x["proxy_gross_r"])
                for x in result["signals"] if x["signal_at"]<=before.timestamp()]
        self.assertEqual(history(original),history(with_future))

    def test_unlabeled_technical_proposals_are_preserved(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        fake=SimpleNamespace(technical_signal="BUY",
            rr_after_spread_estimate=2.,invalidation_level=90.,
            primary_target=130.,strategy="TREND_PULLBACK",
            evidence_score=.8,market_state="TREND_UP")
        with patch("katarina.intelligence.lab.causal_market_replay.MarketDecisionBrain.evaluate",
                   return_value=fake), patch(
            "katarina.intelligence.lab.causal_market_replay.simulate_ohlc_proxy",
            return_value=None):
            result=replay_native_brain({"TEST.vx":self.frames},
                max_m5_cuts_per_symbol=150)
        self.assertEqual(result["signals"],[])
        self.assertGreater(len(result["all_technical_proposals"]),0)
        self.assertTrue(result["proposals_are_selected_before_future_outcomes"])
        self.assertEqual(result["counters"]["quote_path_unavailable"],
                         len(result["all_technical_proposals"]))

    def test_closed_m5_broker_spread_drives_brain_not_assumed_atr(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        snapshots={int(c.closed_at_utc.timestamp()):.075
                   for c in self.frames["M5"]}
        snapshots[int((END+timedelta(minutes=5)).timestamp())]=900.0
        fake=SimpleNamespace(technical_signal="WAIT")
        with patch(
                "katarina.intelligence.lab.causal_market_replay.MarketDecisionBrain.evaluate",
                return_value=fake) as calc:
            result=replay_native_brain(
                {"TEST.vx":self.frames},
                historical_m5_spread_by_symbol={"TEST.vx":snapshots},
                assumed_spread_to_m15_atr=.04,max_m5_cuts_per_symbol=150)
        self.assertGreater(calc.call_count,0)
        self.assertEqual(result["counters"]["spread_unavailable"],0)
        self.assertTrue(result["historical_spread_factual"])
        self.assertFalse(result["next_entry_actual_bidask_verified"])
        self.assertEqual(result["signals"],[])
        self.assertTrue(all(abs(x.kwargs["actual_spread"]-.075)<1e-9
                            for x in calc.call_args_list))

    def test_missing_historical_spread_skips_not_fabricates(self):
        from unittest.mock import patch
        with patch(
                "katarina.intelligence.lab.causal_market_replay.MarketDecisionBrain.evaluate"
                ) as calc:
            result=replay_native_brain(
                {"TEST.vx":self.frames},
                historical_m5_spread_by_symbol={"TEST.vx":{}},
                max_m5_cuts_per_symbol=150)
        calc.assert_not_called()
        self.assertGreater(result["counters"]["spread_unavailable"],0)
        self.assertEqual(result["counters"]["evaluated"],0)
        self.assertEqual(result["orders_sent"],0)

    def test_noncausal_duplicate_and_bad_ohlc_fail_closed(self):
        with self.assertRaises(ValueError):
            validate_bars({**self.frames,"M5":self.frames["M5"]+
                           (self.frames["M5"][-1],)})
        with self.assertRaises(ValueError):
            validate_bars({**self.frames,"M5":(
                replace(self.frames["M5"][0],low=300.),)+
                self.frames["M5"][1:]})

    def test_stop_first_on_same_ohlc_and_cost_survival(self):
        now=END
        candle=SensorCandle(now,100.,101.,99.,100.)
        next_bar=SensorCandle(now+timedelta(minutes=5),100.,105.,95.,100.)
        later=SensorCandle(now+timedelta(minutes=10),100.,101.,99.,100.)
        result=simulate_ohlc_proxy((candle,next_bar,later),0,
                                   "BUY",98.,104.,.1)
        self.assertEqual(result[2],"STOP_FIRST_BID_OHLC_PROXY")
        self.assertLess(result[0],0)

    def test_missing_bar_gap_is_never_painted_as_win(self):
        n=END
        signal=SensorCandle(n,100.,101.,99.,100.)
        far=SensorCandle(n+timedelta(minutes=15),100.,105.,99.,103.)
        last=SensorCandle(n+timedelta(minutes=20),103.,106.,103.,105.)
        self.assertIsNone(simulate_ohlc_proxy((signal,far,last),0,
                                               "BUY",99.,103.,.1))

    def test_purged_train_validation_test_and_holdout(self):
        base=int(END.timestamp())
        rows=[PaperEvent("XAUUSD.vx","TREND_PULLBACK","BUY",
                         base+900*i,base+900*i+7200,
                         0.5,.8,.04,market_regime="TREND_UP") for i in range(100)]
        split=purged_chronological_splits(rows)
        self.assertTrue(split["train"] and split["validation"] and split["test"])
        b1=split["validation"][0].cut
        b2=split["test"][0].cut
        self.assertTrue(all(v.exit_time< b1-7200 for v in split["train"]))
        self.assertTrue(all(v.exit_time< b2-7200 for v in split["validation"]))
        self.assertGreater(split["purged"],0)

    def test_purged_split_rejects_too_short_embargo(self):
        with self.assertRaises(ValueError):
            purged_chronological_splits([],embargo_seconds=60)


if __name__=="__main__": unittest.main()
