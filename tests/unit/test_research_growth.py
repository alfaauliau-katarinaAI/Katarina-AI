from pathlib import Path
from tempfile import TemporaryDirectory
import json,sqlite3,unittest
from katarina.monitoring.research_growth import read_growth,_cache

class GrowthTests(unittest.TestCase):
    def test_real_database_counts_increase_without_inventing_files_or_training(self):
        with TemporaryDirectory() as root:
            root=Path(root);path=root/'experiment-jobs.sqlite3'
            db=sqlite3.connect(path);db.executescript('CREATE TABLE trials(id TEXT PRIMARY KEY,created_utc TEXT,result_json TEXT);CREATE TABLE research_datasets(digest TEXT);CREATE TABLE research_reports(id TEXT);CREATE TABLE gemini_hypotheses(id TEXT);')
            config=json.dumps(dict(method='MOMENTUM',side='BUY',horizon=4,status='NEEDS_FORWARD_VALIDATION',secret='PRIVATE'))
            db.execute('INSERT INTO trials VALUES(?,?,?)',('a'*64,'2026-10-20T01:00:00+00:00',config));db.execute("INSERT INTO research_datasets VALUES('dataset')");db.commit()
            context=sqlite3.connect(root/'context.sqlite3');context.executescript('CREATE TABLE lab_universe(symbol TEXT);INSERT INTO lab_universe VALUES("PRIVATE_SYMBOL");CREATE TABLE research_news_documents(id TEXT);INSERT INTO research_news_documents VALUES("doc");');context.close()
            _cache.clear();a=read_growth(root,42)
            self.assertEqual(a['total_nodes'],4);self.assertEqual(a['total_files'],2);self.assertFalse(a['file_per_node']);self.assertFalse(a['model_training_verified']);self.assertNotIn('PRIVATE',json.dumps(a))
            db.execute('INSERT INTO trials VALUES(?,?,?)',('b'*64,'2026-10-20T01:01:00+00:00',config));db.commit();_cache.clear();b=read_growth(root,42);db.close()
            self.assertEqual(b['total_nodes'],5);self.assertEqual(b['total_files'],a['total_files']);self.assertEqual(b['latest']['record_id'],'b'*64)
    def test_missing_database_is_not_created_or_reported_as_zero_learning(self):
        with TemporaryDirectory() as root:
            _cache.clear();self.assertEqual(read_growth(root,42)['status'],'NOT_ATTESTED');self.assertFalse(list(Path(root).iterdir()))
