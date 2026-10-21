"""Prospective read-only virtual position simulator, no broker fills."""
import unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import sqlite3

from katarina.intelligence.shadow.prospective_shadow_book import (
    ResearchHypothesis,ProspectiveShadowBook,COST_STRESS_R
)

NOW=datetime(2026,10,13,10,0,tzinfo=timezone.utc)


def candidate(*,symbol="XAUUSD.vx",side="BUY",now=NOW,score=.87,
              method="TREND_PULLBACK",regime="TREND_UP",news=False):
    if side=="BUY":
        bid,ask,stop,target=100.,100.1,99.,103.
    else:
        bid,ask,stop,target=100.,100.1,101.2,97.
    return ResearchHypothesis(symbol,method,regime,side,
        now-timedelta(minutes=5),now,bid,ask,now.timestamp(),
        stop,target,score,("policy_missing",),news,.05)


class TestProspectiveShadowBook(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.lab=ProspectiveShadowBook(self.db)
    def tearDown(self):
        self.db.close()

    def test_side_correct_virtual_entry_and_no_real_permission(self):
        result=self.lab.propose([candidate()],NOW)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["mode"],"NO_REAL_ORDERS")
        book=self.lab.summary()
        self.assertFalse(book["usable_for_live_model_promotion"])
        self.assertFalse(book["full_tick_path_verified"])
        self.assertFalse(book["commission_verified"])
        self.assertEqual(book["orders_submitted"],0)
        row=self.db.execute("SELECT entry,stop,target,official_news_verified,state FROM prospective_shadow").fetchone()
        self.assertEqual(row,(100.1,99.,103.,0,"OPEN"))

    def test_buy_exit_uses_bid_and_modeled_cost_stress(self):
        self.lab.propose([candidate()],NOW)
        closed=self.lab.settle(now=NOW+timedelta(minutes=5),
            quotes={"XAUUSD.vx":(103.8,104.0,(NOW+timedelta(minutes=5)).timestamp())})
        self.assertEqual(closed,[("XAUUSD.vx","VIRTUAL_QUOTED")])
        row=self.db.execute("SELECT exit_price,reason,virtual_net_r FROM prospective_shadow").fetchone()
        self.assertEqual(row[0],103.0)   # never pretend better than target
        self.assertEqual(row[1],"SIMULATED_TARGET_QUOTE")
        self.assertAlmostEqual(row[2],(103.-100.1)/(100.1-99.)-COST_STRESS_R)
        self.assertEqual(self.lab.summary()["counts"],{"VIRTUAL_QUOTED":1})

    def test_sell_stop_uses_ask_not_midpoint(self):
        self.lab.propose([candidate(side="SELL")],NOW)
        self.lab.settle(now=NOW+timedelta(minutes=5),
            quotes={"XAUUSD.vx":(100.8,101.4,(NOW+timedelta(minutes=5)).timestamp())})
        row=self.db.execute("SELECT exit_price,reason,virtual_net_r FROM prospective_shadow").fetchone()
        self.assertEqual(row[0],101.4)
        self.assertEqual(row[1],"SIMULATED_STOP_QUOTE")
        self.assertLess(row[2],-1)

    def test_missing_intermediate_quotes_invalidates_not_loss(self):
        self.lab.propose([candidate()],NOW)
        self.lab.settle(now=NOW+timedelta(minutes=11),
            quotes={"XAUUSD.vx":(103.0,103.1,(NOW+timedelta(minutes=11)).timestamp())})
        row=self.db.execute("SELECT state,virtual_net_r,reason FROM prospective_shadow").fetchone()
        self.assertEqual(row,("UNCERTAIN_GAP",None,"unobserved_intratrade_path"))

    def test_absent_quote_expires_invalid(self):
        self.lab.propose([candidate()],NOW)
        self.lab.settle(now=NOW+timedelta(minutes=12),quotes={})
        self.assertEqual(self.lab.summary()["counts"],{"UNCERTAIN_GAP":1})

    def test_clock_lead_and_expired_clock_rejected(self):
        h=replace(candidate(),tick_at=NOW.timestamp()+40)
        self.assertFalse(self.lab.propose([h],NOW)["accepted"])
        h=replace(candidate(),observed_at=NOW+timedelta(minutes=1))
        with self.assertRaises(ValueError):
            self.lab.propose([h],NOW)

    def test_no_expensive_quote_or_invalid_geometry(self):
        h=replace(candidate(),ask=100.9,stop=99.9,target=103.)
        self.assertFalse(self.lab.propose([h],NOW)["accepted"])
        h=replace(candidate(),target=100.2)
        self.assertFalse(self.lab.propose([h],NOW)["accepted"])

    def test_uncertain_regime_never_virtual_opens(self):
        for regime in ("UNKNOWN","TRANSITION","VOLATILITY_SHOCK"):
            self.assertFalse(self.lab.propose([candidate(regime=regime)],NOW)["accepted"])

    def test_technical_without_confirmed_score_cannot_open(self):
        self.assertFalse(self.lab.propose([candidate(score=.61)],NOW)["accepted"])

    def test_deterministic_cross_pair_ranking_independent_of_input_order(self):
        a=candidate(symbol="XAUUSD.vx",score=.75)
        b=candidate(symbol="EURUSD.vx",score=.90)
        res=self.lab.propose([a,b],NOW)
        self.assertTrue(res["accepted"])
        self.assertEqual(res["symbol"],"EURUSD.vx")

    def test_single_virtual_exposure_cap_and_bar_idempotency(self):
        self.lab.propose([candidate()],NOW)
        later=NOW+timedelta(minutes=5)
        more=candidate(symbol="EURUSD.vx",now=later)
        rejected=self.lab.propose([more],later)
        self.assertEqual(rejected["reason"],"ONE_VIRTUAL_PORTFOLIO_POSITION_AT_A_TIME")
        self.assertEqual(self.lab.summary()["counts"]["OPEN"],1)
        self.lab.settle(now=later,quotes={
            "XAUUSD.vx":(103.0,103.1,later.timestamp())})
        replay=self.lab.propose([candidate()],NOW)
        self.assertFalse(replay["accepted"])
        self.assertEqual(replay["reason"],"ALL_PROPOSALS_DUPLICATE")

    def test_cross_restart_sqlite_continuity(self):
        self.lab.propose([candidate()],NOW)
        second=ProspectiveShadowBook(self.db)
        self.assertEqual(second.summary()["counts"],{"OPEN":1})
        self.assertFalse(second.propose([candidate()],NOW)["accepted"])

    def test_timeout_closes_with_only_observed_quote(self):
        self.lab.propose([candidate()],NOW)
        t=NOW
        for i in range(1,25):
            t=NOW+timedelta(minutes=5*i)
            self.lab.settle(now=t,quotes={"XAUUSD.vx":(100.,100.1,t.timestamp())})
        row=self.db.execute("SELECT reason,exit_price FROM prospective_shadow").fetchone()
        self.assertEqual(row,("SIMULATED_TIMED_EXIT_QUOTE",100.))


if __name__=="__main__":unittest.main()
