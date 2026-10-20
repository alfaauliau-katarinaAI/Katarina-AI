import importlib.util
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

spec=importlib.util.spec_from_file_location('memory_export',Path(__file__).resolve().parents[2]/'scripts/memory/export_research_memory.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class MemoryExportTests(unittest.TestCase):
    def test_snapshot_retains_evidence_and_excludes_private_fields(self):
        with TemporaryDirectory() as root, TemporaryDirectory() as out:
            db=sqlite3.connect(Path(root)/'experiment-jobs.sqlite3')
            db.execute('CREATE TABLE trials(id,symbol,digest,created_utc,result_json)')
            db.execute('CREATE TABLE stress_reviews(trial_id,created_utc,result_json)')
            db.execute('CREATE TABLE gemini_hypotheses(created_utc,result_json)')
            value=dict(method='MOMENTUM',side='BUY',lookback=12,horizon=4,threshold=.5,status='INSUFFICIENT_SAMPLES',
                       spread_proxy_price='PRIVATE_PRICE',credential='PRIVATE_TOKEN',development={'n':3,'mean_range_units':.1,'account':'PRIVATE_ACCOUNT'})
            db.execute('INSERT INTO trials VALUES(?,?,?,?,?)',('a'*64,'PRIVATE_SYMBOL','b'*64,'2026-10-19T21:00:00+00:00',json.dumps(value)))
            db.execute('INSERT INTO stress_reviews VALUES(?,?,?)',('COST3:'+'a'*64,'2026-10-19T21:00:01+00:00',json.dumps({'status':'INSUFFICIENT_SAMPLES','secret':'PRIVATE'})))
            db.execute('INSERT INTO gemini_hypotheses VALUES(?,?)',('2026-10-19T21:00:02+00:00',json.dumps({'pattern':'PRIVATE_FREE_TEXT'})))
            db.commit();db.close()
            a=module.snapshot(root,out);content=''.join(p.read_text() for p in Path(out).iterdir())
            self.assertNotIn('PRIVATE',content)
            self.assertEqual(a['experiments'],1);self.assertEqual(a['cost_reviews'],1);self.assertEqual(a['hypotheses'],1)
            self.assertFalse(a['full_private_memory_backup'])
            self.assertEqual(a,module.snapshot(root,out))
