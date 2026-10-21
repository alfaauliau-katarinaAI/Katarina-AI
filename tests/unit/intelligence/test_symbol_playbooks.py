"""Different symbols must not share inherited scalping entry/exit rules."""
import unittest
from datetime import datetime,timezone
from katarina.intelligence.perception.symbol_playbooks import (
    SYMBOLS,FUNCTIONS,CAPS,propose,_make,_ny_open_utc_minutes,_london_start_utc_hour)
from pathlib import Path
import sys

SCRIPTS=Path(__file__).resolve().parents[3]/"scripts"/"research"
sys.path.insert(0,str(SCRIPTS))
from replay_symbol_playbooks import simulate_structure

class SymbolRulesTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,8,20,15,30,tzinfo=timezone.utc)
        self.rows=[]
        for i in range(120):
            price=100+i*.002
            self.rows.append(dict(time=self.now.timestamp()-(120-i)*60,
                open=price,high=price+.1,low=price-.1,
                close=price+.02,tick_volume=100.))
        self.m5=[dict(time=self.now.timestamp()-(120-i)*300,
                open=100,high=100.1,low=99.9,close=100.,
                tick_volume=100.) for i in range(120)]

    def test_sessions_follow_actual_daylight_saving_rules(self):
        july=datetime(2026,7,15,tzinfo=timezone.utc)
        december=datetime(2026,12,15,tzinfo=timezone.utc)
        self.assertEqual(_ny_open_utc_minutes(july,9,30),13*60+30)
        self.assertEqual(_ny_open_utc_minutes(december,9,30),14*60+30)
        self.assertEqual(_london_start_utc_hour(july),7)
        self.assertEqual(_london_start_utc_hour(december),8)

    def test_registered_families_unique(self):
        self.assertEqual(len(SYMBOLS),7)
        self.assertEqual(len(set(SYMBOLS.values())),7)
        self.assertEqual(set(SYMBOLS),set(FUNCTIONS))
        self.assertEqual(set(SYMBOLS),set(CAPS))

    def test_unknown_broker_symbol_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"symbol_playbook_not_registered"):
            propose("XAGUSD.vx",self.rows,self.m5,[],self.now)

    def test_future_candles_rejected(self):
        self.rows[-1]["time"]=self.now.timestamp()
        with self.assertRaisesRegex(ValueError,"unfinished_candle_forbidden"):
            propose("XAUUSD.vx",self.rows,self.m5,[],self.now)

    def test_future_daily_session_rejected(self):
        with self.assertRaisesRegex(ValueError,"day_history_contains_future"):
            propose("US30.vx",self.rows,self.m5,[dict(time=self.now.timestamp())],
                   self.now)

    def test_structural_exit_is_not_generic_atr_mult(self):
        c=_make("XAUUSD.vx","BUY",100,99.5,101.4,35,"gold_test",1)
        self.assertEqual(c[0]["family"],SYMBOLS["XAUUSD.vx"])
        self.assertEqual(c[0]["hypothetical_stop"],99.5)
        self.assertEqual(c[0]["hypothetical_target"],101.4)
        self.assertFalse(c[0]["live_authorized"])
        self.assertEqual(_make("US30.vx","BUY",100,101,102,50,"wrong",1),[])

    def test_bidask_structural_tp_capped_and_MFE(self):
        quote=[(1000.,100.,100.10),(1005.,100.9,101.0)]
        x=simulate_structure(quote,"BUY",99.5,100.7,2100,.01,0)
        self.assertEqual(x["status"],"CLOSED")
        self.assertEqual(x["exit_reason"],"TP")
        self.assertAlmostEqual(x["R"],(.6/.6))
        self.assertGreater(x["mfe_R"],0)

    def test_sell_gap_must_use_worse_quote(self):
        quote=[(1000.,100.,100.1),(1003.,101.9,102.0)]
        x=simulate_structure(quote,"SELL",100.5,98.0,2100,.01,1)
        self.assertEqual(x["exit_reason"],"SL")
        self.assertLess(x["R"],-1)

    def test_missing_time_exit_not_fabricated(self):
        quote=[(1000.,100.,100.1),(1100.,100.2,100.3)]
        x=simulate_structure(quote,"BUY",99.,102.,2100,.01,0)
        self.assertEqual(x["status"],"EXIT_QUOTE_MISSING")

    def test_spread_slippage_decreases_win_r(self):
        ticks=[(1000.,100.,100.1),(1001.,101.5,101.6)]
        a=simulate_structure(ticks,"BUY",99.5,101.,2100,.01,0)
        b=simulate_structure(ticks,"BUY",99.5,101.,2100,.01,3)
        self.assertLess(b["R"],a["R"])
        self.assertEqual(a["exit_reason"],"TP")
        self.assertEqual(b["exit_reason"],"TP")

if __name__=="__main__":
    unittest.main()
