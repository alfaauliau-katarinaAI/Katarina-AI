import unittest
from datetime import datetime,timedelta,timezone

from katarina.intelligence.news.news_intelligence import MultiSourceNewsEngine, NewsItem


class MultiSourceNewsTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,6,12,0,tzinfo=timezone.utc)
        self.engine=MultiSourceNewsEngine()

    def test_deduplicate_prefers_more_trusted_source(self):
        items=[
            NewsItem("ap",self.now-timedelta(minutes=5),"Fed keeps rates unchanged",("USD",),3),
            NewsItem("fed",self.now-timedelta(minutes=5),"Fed keeps rates unchanged",("USD",),3),
        ]
        d=self.engine.deduplicate(items)
        self.assertEqual(len(d),1)
        self.assertEqual(d[0].source_id,"fed")

    def test_gold_matches_usd_and_gold_news(self):
        items=[
            NewsItem("fed",self.now-timedelta(minutes=60),"Fed policy statement",("USD","GOLD"),3,sentiment=-.2),
        ]
        c=self.engine.assess(items,exposures=("USD","GOLD","METALS"),now_utc=self.now)
        self.assertTrue(c.ready)
        self.assertFalse(c.blackout)
        self.assertEqual(c.matched_items,1)

    def test_oil_matches_energy_sources(self):
        items=[
            NewsItem("eia",self.now-timedelta(minutes=20),"US crude inventories rise",("OIL","ENERGY"),2),
        ]
        c=self.engine.assess(items,exposures=("USD","OIL","ENERGY"),now_utc=self.now)
        self.assertTrue(c.ready)
        self.assertEqual(c.source_count,1)

    def test_crypto_can_use_regulatory_context(self):
        items=[
            NewsItem("sec",self.now-timedelta(minutes=10),"Digital asset regulatory update",("CRYPTO","BTC","USD"),2),
        ]
        c=self.engine.assess(items,exposures=("BTC","CRYPTO","USD"),now_utc=self.now)
        self.assertTrue(c.ready)

    def test_missing_relevant_context_fails_closed(self):
        items=[NewsItem("ecb",self.now-timedelta(minutes=10),"ECB update",("EUR",),2)]
        c=self.engine.assess(items,exposures=("BTC","CRYPTO"),now_utc=self.now)
        self.assertFalse(c.ready)
        self.assertTrue(c.blackout)

    def test_high_impact_near_now_blackout(self):
        items=[NewsItem("bls",self.now+timedelta(minutes=10),"NFP release",("USD","FX"),3)]
        c=self.engine.assess(items,exposures=("EUR","USD","FX"),now_utc=self.now)
        self.assertTrue(c.blackout)


if __name__=="__main__": unittest.main()
