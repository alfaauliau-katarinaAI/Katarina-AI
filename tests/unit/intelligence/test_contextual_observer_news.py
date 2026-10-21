"""Full-body official news and one canonical no-orders observer evidence."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import sqlite3

from katarina.intelligence.verified_policy_context import (
    _host_ok,parse_full_article,_policy_signal,ReadArticle,evidence_from_article,item_from_article,instrument_currencies,
)
from katarina.intelligence.contextual_observation_journal import ContextDecisionJournal

NOW=datetime(2026,10,12,8,0,tzinfo=timezone.utc)


def long_text(text):
    context=("The statement explains the current economy and inflation; "
             "the committee reviewed economic conditions and employment. "
             "Officials reported recent trends in financial conditions and "
             "uncertainty remains elevated in some sectors. ")
    return "\n".join([text,context*9])


def article(body,*,source="fed",url=None,published=None):
    return ReadArticle(
        source_id=source,
        url=url or "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261012a.htm",
        title="Federal Reserve releases statement",
        published_at_utc=published or NOW-timedelta(minutes=45),
        observed_at_utc=NOW-timedelta(minutes=20),
        body=body,sha256=sha256(body.encode()).hexdigest())


class TestVerifiedFullBodyPolicy(unittest.TestCase):
    def test_url_allowlist_blocks_private_fetch_and_redirect_targets(self):
        for uri in ("http://www.federalreserve.gov/news",
                    "https://federalreserve.gov.evil.tld/story",
                    "https://127.0.0.1/story",
                    "https://user:pass@www.federalreserve.gov/story",
                    "https://www.ecb.europa.eu/story"):
            self.assertFalse(_host_ok(uri,"fed"))
        self.assertTrue(_host_ok("https://www.federalreserve.gov/news","fed"))

    def test_html_requires_body_not_title(self):
        title="<html><head><title>Fed raises rates</title></head><body>"
        tiny=(title+"<p>Statement appeared.</p></body></html>").encode()
        with self.assertRaises(ValueError):parse_full_article(tiny,"fed")
        html=(title+"".join("<p>"+x+"</p>" for x in long_text(
            "The Federal Open Market Committee decided to lower the target range "
            "for the federal funds rate.").splitlines())+"</body></html>").encode()
        self.assertGreater(len(parse_full_article(html,"fed").split()),95)

    def test_fed_rate_cut_full_article_gold_buy_hypothesis(self):
        body=long_text("The Committee decided to lower the target range "
                       "for the federal funds rate by 25 basis points.")
        e=evidence_from_article(article(body),"XAUUSD.vx",NOW)
        self.assertIsNotNone(e)
        self.assertEqual(e.favored_side,"BUY")
        self.assertTrue(e.source_verified)
        self.assertTrue(e.significant)
        self.assertIn("EASING",e.policy_direction)
        self.assertIsNotNone(item_from_article(article(body),"XAUUSD.vx",NOW))

    def test_fed_rise_eurusd_sell_but_index_uncertain(self):
        body=long_text("The Committee voted to raise the target range "
                       "for the federal funds rate by 25 basis points.")
        self.assertEqual(evidence_from_article(article(body),"EURUSD.vx",NOW).favored_side,"SELL")
        nas=evidence_from_article(article(body),"NAS100.vx",NOW)
        self.assertEqual(nas.favored_side,"UNCERTAIN")
        self.assertFalse(nas.significant)

    def test_headline_alone_never_creates_policy_trading_bias(self):
        body=long_text("The Committee described the economy and "
                       "reviewed inflation, employment and growth.")
        e=evidence_from_article(replace(
            article(body),title="Fed hikes rates"),"XAUUSD.vx",NOW)
        self.assertEqual(e.favored_side,"UNCERTAIN")
        self.assertEqual(e.policy_direction.split(": ")[1].split(" ")[0],"UNCERTAIN")

    def test_conflicting_policy_sentences_never_decide_side(self):
        body=long_text(
            "The committee decided to raise the federal funds rate. "
            "The committee decided to lower the federal funds rate.")
        self.assertEqual(_policy_signal(body,"fed"),"UNCERTAIN")

    def test_future_article_or_untrusted_digest_rejected(self):
        body=long_text("The committee decided to lower the federal funds rate.")
        with self.assertRaises(ValueError):
            evidence_from_article(replace(article(body),
                observed_at_utc=NOW+timedelta(seconds=1)),"XAUUSD.vx",NOW)
        with self.assertRaises(ValueError):
            evidence_from_article(replace(article(body),sha256="wrong"),"XAUUSD.vx",NOW)

    def test_wrong_currency_is_excluded(self):
        body=long_text("The committee decided to lower the federal funds rate.")
        self.assertIsNone(evidence_from_article(article(body),"EURJPY.vx",NOW))
        self.assertEqual(instrument_currencies("GBPJPY.vx"),("GBP","JPY"))


class TestContextualJournal(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.ledger=ContextDecisionJournal(self.db)
        self.start=NOW-timedelta(minutes=5)
        self.args=dict(symbol="XAUUSD.vx",
                       closed_m5_utc=self.start.isoformat(),
                       observed_utc=NOW.isoformat(),
                       side="SELL",method="TREND_EXPANSION_V9",
                       decision="WAIT",blockers=("not_validated",),
                       bid=4210.,ask=4210.50,tick_epoch=NOW.timestamp())

    def tearDown(self):
        self.db.close()

    def test_idempotent_per_symbol_closed_bar(self):
        self.assertTrue(self.ledger.record(**self.args))
        self.assertFalse(self.ledger.record(**self.args))
        self.assertEqual(self.ledger.summary()["counts"],{"PENDING":1})

    def test_wait_is_recorded_without_pretending_a_fill(self):
        args={**self.args,"side":"WAIT"}
        self.assertTrue(self.ledger.record(**args))
        result=self.ledger.summary()
        self.assertEqual(result["counts"],{"NO_SIGNAL":1})
        self.assertFalse(result["usable_as_ResolvedExperience"])

    def test_future_candle_and_bad_quote_fail_closed(self):
        with self.assertRaises(ValueError):
            self.ledger.record(**{**self.args,
                "closed_m5_utc":(NOW+timedelta(minutes=1)).isoformat()})
        with self.assertRaises(ValueError):
            self.ledger.record(**{**self.args,"ask":4190.})

    def test_late_quote_never_reconstructed(self):
        self.assertTrue(self.ledger.record(**self.args))
        n=NOW+timedelta(minutes=18)
        quoted=self.ledger.resolve({"XAUUSD.vx":(4200,4200.50,n.timestamp())},n)
        self.assertEqual(quoted,0)
        self.assertEqual(self.ledger.summary()["counts"],{"MISSING_EXIT":1})

    def test_resolve_late_with_real_broker_due_window(self):
        self.ledger.record(**self.args)
        due=(NOW+timedelta(minutes=15)).timestamp()
        checked=[]
        def lookup(symbol,due_epoch,when):
            checked.append((symbol,due_epoch,when))
            return (4200.,4200.4,due_epoch+.5)
        n=NOW+timedelta(minutes=20)
        count=self.ledger.resolve({},n,quote_lookup=lookup)
        self.assertEqual(count,1)
        self.assertEqual(self.ledger.summary()["counts"],
                         {"BROKER_TICK_RECONCILED":1})
        self.assertEqual(len(checked),1)
        self.assertEqual(checked[0][0],"XAUUSD.vx")
        self.assertAlmostEqual(checked[0][1],due)
        self.assertFalse(self.ledger.summary()["usable_as_ResolvedExperience"])

    def test_recover_old_missing_after_fix_distinct_status(self):
        self.ledger.record(**self.args)
        n=NOW+timedelta(minutes=20)
        self.assertEqual(self.ledger.resolve({},n),0)
        self.assertEqual(self.ledger.summary()["counts"],{"MISSING_EXIT":1})
        def lookup(symbol,due,when):
            return (4200.,4200.4,due+1.)
        self.assertEqual(self.ledger.reconcile_missing(lookup,n),1)
        self.assertEqual(self.ledger.reconcile_missing(lookup,n),0)
        self.assertEqual(self.ledger.summary()["counts"],
                         {"BROKER_TICK_RECOVERED":1})
        self.assertFalse(self.ledger.summary()["usable_as_ResolvedExperience"])

    def test_future_or_after_tolerance_quote_fails_closed(self):
        self.ledger.record(**self.args)
        n=NOW+timedelta(minutes=20)
        count=self.ledger.resolve({},n,quote_lookup=lambda s,d,w:
                                  (4200.,4200.4,w+5.))
        self.assertEqual(count,0)
        self.assertEqual(self.ledger.summary()["counts"],{"MISSING_EXIT":1})
        self.assertEqual(self.ledger.reconcile_missing(lambda s,d,w:
            (4200.,4200.4,d+130.),n),0)

    def test_due_time_uses_mt5_entry_tick_not_vps_wall(self):
        args={**self.args,"tick_epoch":NOW.timestamp()-12}
        self.assertTrue(self.ledger.record(**args))
        due=self.db.execute(
            "SELECT due_epoch FROM contextual_decisions").fetchone()[0]
        self.assertAlmostEqual(due,NOW.timestamp()-12+900)
        resolution_at=NOW+timedelta(minutes=15)
        self.assertEqual(self.ledger.resolve({},resolution_at,
            quote_lookup=lambda symbol,due,now:
                (4200.,4200.4,due+1)),1)
        self.assertEqual(self.ledger.summary()["counts"],
                         {"BROKER_TICK_RECONCILED":1})

    def test_future_mt5_entry_tick_cannot_be_logged(self):
        with self.assertRaises(ValueError):
            self.ledger.record(**{**self.args,
                "tick_epoch":NOW.timestamp()+1})

    def test_observed_ask_bid_markout_is_not_trade_pnl(self):
        self.ledger.record(**self.args)
        due=NOW+timedelta(minutes=15)
        resolved=self.ledger.resolve(
            {"XAUUSD.vx":(4200.,4200.4,due.timestamp())},due)
        self.assertEqual(resolved,1)
        self.assertEqual(self.ledger.summary()["counts"],{"QUOTED":1})
        self.assertIn("NOT_EXECUTED_TRADING_PNL",
                      self.ledger.summary()["outcome_type"])
        row=self.db.execute(
            "SELECT markout_bps FROM contextual_decisions").fetchone()[0]
        self.assertGreater(row,0)


if __name__=="__main__":
    unittest.main()
