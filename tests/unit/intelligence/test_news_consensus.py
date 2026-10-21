import unittest
from datetime import datetime,timezone

from katarina.intelligence.news.news_consensus import NewsConsensusEngine
from katarina.intelligence.news.news_intelligence import NewsItem


NOW=datetime(2026,10,6,12,0,tzinfo=timezone.utc)


class NewsConsensusTests(unittest.TestCase):
    def test_single_official_source_is_authoritative(self):
        r=NewsConsensusEngine().assess([NewsItem("fed",NOW,"Fed statement",("USD",),3,.2)])
        self.assertTrue(r.ready)
        self.assertTrue(r.official_source_present)

    def test_single_nonofficial_source_is_not_enough(self):
        r=NewsConsensusEngine().assess([NewsItem("reuters",NOW,"Market report",("USD",),2,.1)])
        self.assertFalse(r.ready)
        self.assertEqual(r.reason,"insufficient_independent_sources")

    def test_two_independent_market_sources_are_usable(self):
        items=[
            NewsItem("reuters",NOW,"Market A",("USD",),2,.2),
            NewsItem("bloomberg",NOW,"Market B",("USD",),2,.2),
        ]
        r=NewsConsensusEngine().assess(items)
        self.assertTrue(r.ready)
        self.assertEqual(r.independent_sources,2)

    def test_conflicting_sources_reduce_consensus(self):
        same=[
            NewsItem("reuters",NOW,"A",("USD",),2,.8),
            NewsItem("bloomberg",NOW,"B",("USD",),2,.7),
        ]
        conflict=[
            NewsItem("reuters",NOW,"A",("USD",),2,.8),
            NewsItem("bloomberg",NOW,"B",("USD",),2,-.7),
        ]
        a=NewsConsensusEngine().assess(same)
        b=NewsConsensusEngine().assess(conflict)
        self.assertTrue(b.conflict)
        self.assertLess(b.consensus,a.consensus)


if __name__=="__main__": unittest.main()
