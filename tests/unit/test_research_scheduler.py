from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import json,sqlite3,tempfile,unittest,threading
from katarina.intelligence.autonomous_research import ResearchPool,preserve_dataset
from katarina.monitoring.research_health import read_research_health

class Trace:
    def __init__(self):self.events=[]
    def emit(self,*args,**kw):self.events.append((args,kw))

class ResearchSchedulerTests(unittest.TestCase):
    def setup_db(self,root):
        with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db,db:
            db.execute('CREATE TABLE trials(id TEXT PRIMARY KEY,symbol,digest,created_utc,result_json)')
            db.execute('CREATE TABLE gemini_hypotheses(created_utc,result_json)')
            db.execute('CREATE TABLE stress_reviews(trial_id TEXT PRIMARY KEY,created_utc,result_json)')
            rows=[[1000+i*3600,10,12,8,10] for i in range(512)]
            from hashlib import sha256
            digest=sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest();preserve_dataset(db,digest,rows)
            for ident,status in [('bad','REJECTED_IN_HISTORICAL_REVIEW'),('small','INSUFFICIENT_SAMPLES'),('good','NEEDS_FORWARD_VALIDATION')]:
                db.execute('INSERT INTO trials VALUES(?,?,?,?,?)',(ident,'EURUSD',digest,'2026-10-20T00:00:00+00:00',json.dumps(dict(status=status))))

    def test_only_viable_trials_are_reviewed_once_per_cost_level(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.setup_db(root);trace=Trace();pool=ResearchPool(root,trace)
            with patch('katarina.intelligence.research_capacity.research_capacity',return_value={'status':'READY'}),patch('katarina.intelligence.autonomous_research.cost_review',return_value={'status':'NEEDS_FORWARD_VALIDATION'}) as evaluate:
                self.assertTrue(pool.review_one(2));self.assertTrue(pool.review_one(3))
                self.assertFalse(pool.review_one(2));self.assertFalse(pool.review_one(3));self.assertEqual(evaluate.call_count,2)
            with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db:
                self.assertEqual({r[0] for r in db.execute('SELECT trial_id FROM stress_reviews')},{'good','COST3:good'})
            self.assertEqual(pool.review_states[2]['status'],'WAITING_ELIGIBLE_CANDIDATE')
            h=read_research_health(root,123,allowed=True);self.assertEqual(h['eligible_candidates'],1);self.assertEqual(h['pending_cost2'],0)

    def test_low_disk_blocks_reviews_and_model_calls_before_database_writes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);model=unittest.mock.Mock();pool=ResearchPool(root,Trace(),model)
            with patch('katarina.intelligence.research_capacity.research_capacity',return_value={'status':'PAUSED_LOW_DISK'}):
                self.assertFalse(pool.review_one(2));self.assertFalse(pool.model_once())
            self.assertFalse((root/'experiment-jobs.sqlite3').exists());model.complete.assert_not_called()
            self.assertEqual(pool.review_states[2]['status'],'PAUSED_LOW_DISK')
