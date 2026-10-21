"""Causal bid/ask TP/SL path tests; no trade routing."""
import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path

SCRIPTS=Path(__file__).resolve().parents[3]/"scripts"/"research"
sys.path.insert(0,str(SCRIPTS))
from historical_shadow_ticks import snapshot_hash
from replay_historical_tick_stops import (
    simulate,recovered_atr,historical_path,summarize,normalized_ticks,
)

class TickPathTests(unittest.TestCase):
    def setUp(self):
        self.entry=(1000.,100.,100.1)

    def test_buy_tp_uses_bid_and_caps_positive_gap(self):
        e=simulate([self.entry,(1001.,101.6,101.8)],
                   "BUY",1.,1.,1.)
        self.assertEqual(e["status"],"CLOSED")
        self.assertEqual(e["exit_reason"],"TP")
        self.assertAlmostEqual(e["quoted_delta"],1.)
        self.assertAlmostEqual(e["stressed_r"],1.)

    def test_buy_stop_uses_worse_actual_bid_on_gap(self):
        e=simulate([self.entry,(1001.,98.,98.2)],
                   "BUY",1.,2.,1.)
        self.assertEqual(e["exit_reason"],"SL")
        self.assertAlmostEqual(e["quoted_delta"],-2.1)

    def test_sell_tp_is_ask_and_no_favorable_slippage(self):
        e=simulate([self.entry,(1002.,98.,98.3)],
                   "SELL",1.,1.,1.)
        self.assertEqual(e["exit_reason"],"TP")
        self.assertAlmostEqual(e["quoted_delta"],1.)

    def test_sell_stop_gap_worsens_loss(self):
        e=simulate([self.entry,(1002.,101.8,102.)],
                   "SELL",1.,1.,1.)
        self.assertEqual(e["exit_reason"],"SL")
        self.assertAlmostEqual(e["quoted_delta"],-2.)

    def test_time_exit_uses_last_bid_after_duration(self):
        e=simulate([self.entry,(1010.,100.3,100.4),
                    (1020.,100.4,100.5)],"BUY",1.,3.,1.,max_hold=20)
        self.assertEqual(e["exit_reason"],"TIME")
        self.assertAlmostEqual(e["quoted_delta"],.3)

    def test_midtrade_missing_ticks_do_not_invent_wins(self):
        e=simulate([self.entry,(1200.,101.8,102.)],"BUY",1.,1.,1.)
        self.assertEqual(e["status"],"DATA_GAP")

    def test_full_duration_without_exit_tick_fails_closed(self):
        e=simulate([self.entry,(1100.,100.3,100.4)],"BUY",1.,5.,5.,
                   max_hold=1800)
        self.assertEqual(e["status"],"TIME_QUOTE_MISSING")

    def test_extra_bps_stress_is_not_double_charging_spread(self):
        ticks=[self.entry,(1001.,101.1,101.3)]
        a=simulate(ticks,"BUY",1.,1.,1.,extra_cost_bps=0)
        b=simulate(ticks,"BUY",1.,1.,1.,extra_cost_bps=5)
        self.assertAlmostEqual(a["quoted_bps"]-b["stressed_bps"],5.)
        self.assertLess(b["stressed_r"],a["stressed_r"])

    def test_missing_entry_quote_in_historical_retrieval(self):
        class MT:
            COPY_TICKS_ALL=0
            def copy_ticks_range(self,*a):
                return [dict(time_msc=1000000,bid=100.5,ask=100.6)]
        entry=dict(entry_tick_utc=datetime.fromtimestamp(1000,timezone.utc).isoformat(),
                   entry_bid=100,entry_ask=100.1)
        ticks,error=historical_path(MT(),"DEMO",entry)
        self.assertIsNone(ticks)
        self.assertEqual(error,"entry_quote_not_reproduced")

    def test_invalid_quote_fails_closed(self):
        raw=[dict(time_msc=1000000,bid=100.,ask=0)]
        ticks,error=normalized_ticks(raw)
        self.assertEqual(error,"invalid_tick_quote")
        self.assertEqual(ticks,[])

    def test_reconstruct_closed_atr_only_with_matching_hash(self):
        rates=[]
        for i in range(120):
            rates.append(dict(time=float(i*60),open=100.0,
                high=100.5,low=99.5,close=100.0,tick_volume=100))
        fingerprint=snapshot_hash(rates)
        atr,error=recovered_atr(rates,120*60,60,fingerprint)
        self.assertIsNone(error)
        self.assertAlmostEqual(atr,1.)
        wrong,error=recovered_atr(rates,120*60,60,"0"*64)
        self.assertIsNone(wrong)
        self.assertEqual(error,"history_fingerprint_mismatch")

    def test_summary_keeps_missing_denominator(self):
        common=dict(signal_bar_close_utc="2026-10-08T10:00:00+00:00",
                    extra_cost_bps=2.)
        data=[dict(**common,status="CLOSED",stressed_r=-1.0,exit_reason="SL"),
              dict(**common,status="DATA_GAP"),
              dict(**common,status="OVERLAP_EXCLUDED")]
        result=summarize(data)
        self.assertEqual(result["n_candidates"],3)
        self.assertEqual(result["n_closed"],1)
        self.assertEqual(result["missing"]["DATA_GAP"],1)
        self.assertEqual(result["status"],"INSUFFICIENT_EVIDENCE")
        self.assertAlmostEqual(result["outcome_coverage_fraction"],1/3)

if __name__=="__main__":
    unittest.main()
