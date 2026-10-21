"""Virtual prospective memory cannot promote itself to verified broker alpha."""
import sqlite3
import unittest
from datetime import datetime,timedelta,timezone

from katarina.intelligence.shadow.prospective_shadow_book import (
    ProspectiveShadowBook,ResearchHypothesis,
)
from katarina.intelligence.shadow.prospective_shadow_review import (
    summarize,pause_due_to_losses,
)
NOW=datetime(2026,10,13,10,0,tzinfo=timezone.utc)
SYMBOL="XAUUSD.vx"


def buy(t):
    return ResearchHypothesis(
        symbol=SYMBOL,method="TREND_PULLBACK",regime="TREND_UP",
        side="BUY",closed_bar_at=t-timedelta(minutes=5),
        observed_at=t,bid=100.,ask=100.1,tick_at=t.timestamp(),
        stop=99.,target=103.,evidence_score=.9,
        blockers=("macro_not_proven",),official_news_verified=False,
        spread_atr=.06,
    )


class ShadowForwardReviewTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.book=ProspectiveShadowBook(self.db)

    def tearDown(self):
        self.db.close()

    def close_loss(self,t):
        self.assertTrue(self.book.propose([buy(t)],t)["accepted"])
        exit_at=t+timedelta(minutes=5)
        self.book.settle(now=exit_at,quotes={
            SYMBOL:(98.5,98.7,exit_at.timestamp())})

    def test_insufficient_is_not_approved_alpha(self):
        self.close_loss(NOW)
        info=summarize(self.db,NOW+timedelta(minutes=6))
        self.assertFalse(info["cannot_authorize_real_execution"] is False)
        self.assertTrue(info["cannot_convert_into_verified_ResolvedExperience"])
        self.assertEqual(info["groups"][0]["complete"],1)
        self.assertEqual(info["groups"][0]["diagnostic_status"],"INSUFFICIENT_SAMPLE")

    def test_future_outcomes_never_contribute_to_earlier_memory(self):
        self.close_loss(NOW)
        self.assertEqual(summarize(self.db,NOW)["groups"],[])
        self.assertEqual(summarize(self.db,NOW+timedelta(minutes=6))["groups"][0]["complete"],1)

    def test_five_consecutive_losses_pause_virtual_only(self):
        for i in range(5):
            self.close_loss(NOW+timedelta(minutes=10*i))
        after=NOW+timedelta(minutes=50)
        self.assertTrue(pause_due_to_losses(self.db,
            symbol=SYMBOL,method="TREND_PULLBACK",
            side="BUY",regime="TREND_UP",at_utc=after))
        retry=self.book.propose([buy(after)],after)
        self.assertFalse(retry["accepted"])
        self.assertEqual(retry["drift_paused"],1)
        # Pause expires; historic loss results remain archived.
        later=after+timedelta(days=2)
        self.assertFalse(pause_due_to_losses(self.db,
            symbol=SYMBOL,method="TREND_PULLBACK",
            side="BUY",regime="TREND_UP",at_utc=later))

    def test_result_scope_never_borrows_other_symbol(self):
        self.close_loss(NOW)
        self.assertFalse(pause_due_to_losses(self.db,
            symbol="EURUSD.vx",method="TREND_PULLBACK",
            side="BUY",regime="TREND_UP",
            at_utc=NOW+timedelta(minutes=6)))


if __name__=="__main__":unittest.main()
