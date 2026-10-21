"""Cross-pair rank is point-in-time and never allowed to promise daily return."""
import unittest
from datetime import datetime,timedelta,timezone
from dataclasses import replace
from katarina.intelligence.perception.multi_pair_arbitrator import (
    Opportunity,RiskLimits,select_at_checkpoint,portfolio_replay)
NOW=datetime(2026,9,1,12,tzinfo=timezone.utc)
def opportunity(name,score=.8,when=NOW):
    return Opportunity(name,when,"BUY","TREND_PULLBACK",score,2.0,.08,
         True,True,True,False)
class TestMultiPairArbitrator(unittest.TestCase):
    def test_rank_highest_at_same_timestamp(self):
        lo=opportunity("EURUSD",.71);hi=opportunity("US30",.91)
        a=select_at_checkpoint([lo,hi],cut_utc=NOW,hypothesis_news_clear=True)
        self.assertEqual(a.selected.symbol,"US30")
        self.assertEqual(len(a.valid),2)
        self.assertFalse(a.live_execution_authorized)
    def test_news_unverified_is_no_trade_by_default(self):
        a=select_at_checkpoint([opportunity("US30")],cut_utc=NOW)
        self.assertIsNone(a.selected)
        self.assertIn("news_context_unverified",a.reasons)
    def test_stale_future_and_bad_rr_are_rejected(self):
        x=opportunity("US30",.94,when=NOW+timedelta(minutes=5))
        y=replace(opportunity("EURUSD"),structural_rr=.7)
        a=select_at_checkpoint([x,y],cut_utc=NOW,hypothesis_news_clear=True)
        self.assertIsNone(a.selected)
    def test_future_outcomes_cannot_choose_candidate(self):
        a=opportunity("Top",.96);b=opportunity("Low",.7)
        groups=[(NOW,[a,b])]
        outcomes={
            ("Top",int(NOW.timestamp())):dict(R=-1.,exit_time=int((NOW+timedelta(minutes=40)).timestamp())),
            ("Low",int(NOW.timestamp())):dict(R=1.8,exit_time=int((NOW+timedelta(minutes=40)).timestamp()))
        }
        x=portfolio_replay(groups,outcomes,hypothesis_news_clear=True)
        self.assertEqual(x["trades"][0]["symbol"],"Top")
        self.assertLess(x["equity_multiple"],1.)
    def test_one_trade_per_day_even_if_more_candidates(self):
        t=NOW+timedelta(hours=6)
        groups=[(NOW,[opportunity("A",when=NOW)]),(t,[opportunity("B",when=t)])]
        outcomes={
          ("A",int(NOW.timestamp())):dict(R=1.0,exit_time=int((NOW+timedelta(minutes=20)).timestamp())),
          ("B",int(t.timestamp())):dict(R=1.0,exit_time=int((t+timedelta(minutes=20)).timestamp()))
        }
        x=portfolio_replay(groups,outcomes,hypothesis_news_clear=True)
        self.assertEqual(len(x["trades"]),1)
        self.assertEqual(x["capacity_rejections"],1)
    def test_no_selected_trades_fails_to_trade_not_fabricated_profit(self):
        x=portfolio_replay([(NOW,[])],{},hypothesis_news_clear=True)
        self.assertEqual(len(x["trades"]),0)
        self.assertEqual(x["equity_multiple"],1.)
    def test_invalid_limits_rejected(self):
        with self.assertRaises(ValueError):RiskLimits(risk_fraction=.05)
if __name__=="__main__":unittest.main()