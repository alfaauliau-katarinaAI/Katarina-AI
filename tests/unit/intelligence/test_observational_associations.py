from datetime import datetime,timezone
import sqlite3
import unittest
from katarina.intelligence.perception.observational_associations import observe_associations,pearson


class AssociationTests(unittest.TestCase):
    def test_known_positive_negative_and_constant_relationships(self):
        self.assertEqual(pearson([(i,i*2) for i in range(25)])['pearson'],1)
        self.assertEqual(pearson([(i,-i) for i in range(25)])['pearson'],-1)
        self.assertIsNone(pearson([(i,1) for i in range(25)])['pearson'])
        self.assertEqual(pearson([(1,2)])['status'],'INSUFFICIENT_SAMPLES')

    def test_wait_independent_quotes_are_deduplicated_and_current_bucket_excluded(self):
        db=sqlite3.connect(':memory:')
        now=datetime.fromtimestamp(18000,tz=timezone.utc)
        for _ in range(2):
            result=observe_associations(db,{'A':(100,102,18000)},now)
        self.assertEqual(result['quote_points'],{'A':1})
        self.assertEqual(result['return_points'],{'A':0})
        self.assertFalse(result['strategy_validated'])
        self.assertFalse(result['live_execution_authorized'])
        db.close()

    def test_no_gap_returns_and_only_common_completed_buckets(self):
        db=sqlite3.connect(':memory:')
        for step in range(24):
            now=datetime.fromtimestamp(18000+step*300,tz=timezone.utc)
            observe_associations(db,{'A':(100+step**2,100+step**2,now.timestamp()),
                'B':(200+step**2,200+step**2,now.timestamp())},now)
        result=observe_associations(db,{},datetime.fromtimestamp(26000,tz=timezone.utc))
        self.assertEqual(result['price_return_correlations'],[])
        result=observe_associations(db,{'A':(700,700,26000),'B':(800,800,26000)},
                                     datetime.fromtimestamp(26000,tz=timezone.utc))
        self.assertEqual(result['price_return_correlations'][0]['n'],23)
        self.assertIsNotNone(result['price_return_correlations'][0]['pearson'])
        db.close()

    def test_future_or_bad_quote_rejected(self):
        db=sqlite3.connect(':memory:')
        with self.assertRaises(ValueError):
            observe_associations(db,{'A':(100,102,18001)},datetime.fromtimestamp(18000,tz=timezone.utc))
        db.close()

    def test_future_and_corrupt_news_never_become_features(self):
        db=sqlite3.connect(':memory:')
        db.execute('CREATE TABLE contextual_market_articles(published,fetched,body,sha256)')
        db.execute('INSERT INTO contextual_market_articles VALUES(?,?,?,?)',
            ('2026-10-16T12:00:00+00:00','2026-10-16T11:00:00+00:00','body','wrong'))
        result=observe_associations(db,{},datetime(2026,10,16,13,tzinfo=timezone.utc))
        self.assertEqual(result['verified_article_times'],0)
        self.assertEqual(result['rejected_article_times'],1)
        db.close()
