from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
from katarina.intelligence.lab.autonomous_research import ResearchWorker, evaluate, GRID
from katarina.intelligence.lab.continuous_research_lab import setup
from katarina.monitoring.activity_trace import ActivityTrace


def bars():
    return [(3600*i,100+i*.1,101+i*.1,99+i*.1,100.2+i*.1) for i in range(700)]


class AutonomousResearchTests(unittest.TestCase):
    def test_chronological_review_cannot_change_development(self):
        rows=bars();config=('MOMENTUM',1,12,4,.5)
        first=evaluate(rows,config,.01)
        changed=[r if i<len(rows)*2//3 else (r[0],r[1]*2,r[2]*2,r[3]*2,r[4]*2) for i,r in enumerate(rows)]
        self.assertEqual(first['development'],evaluate(changed,config,.01)['development'])
        self.assertGreater(first['development']['n'],30)
        self.assertFalse(first['independent_holdout'])
        self.assertFalse(first['live_authorized'])

    def test_resume_deduplicates_and_exhausted_queue_waits(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with closing(sqlite3.connect(root/'context.sqlite3')) as db, db:
                setup(db);db.execute("INSERT INTO lab_universe(symbol) VALUES('FIXTURE')")
                db.executemany('INSERT INTO lab_bars VALUES(?,?,?,?,?,?)',[('FIXTURE',*r) for r in bars()])
                db.execute('INSERT INTO lab_runs VALUES(?,?,?,?,?)',('source','FIXTURE','2026-01-01','x',json.dumps({'spread_proxy_price':.01})))
            trace=ActivityTrace(root)
            with patch('katarina.intelligence.lab.autonomous_research.GRID',GRID[:2]),patch('katarina.intelligence.lab.research_capacity.research_capacity',return_value={'status':'READY'}):
                self.assertTrue(ResearchWorker(root,trace).tick())
                self.assertTrue(ResearchWorker(root,trace).tick())
                worker=ResearchWorker(root,trace);self.assertFalse(worker.tick())
                self.assertEqual(worker.state['completed'],2)
                self.assertEqual(worker.state['status'],'WAITING_NEW_DATA')
            with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM trials').fetchone()[0],2)
            self.assertFalse((root/'continuous.stop').exists())

    def test_simultaneous_trace_writers_have_unique_events(self):
        with tempfile.TemporaryDirectory() as directory:
            trace=ActivityTrace(directory)
            threads=[threading.Thread(target=lambda:[trace.emit('EXPERIMENT','DONE',count=1) for _ in range(20)]) for _ in range(3)]
            for t in threads:t.start()
            for t in threads:t.join()
            data=json.loads((Path(directory)/'runtime-activity.json').read_text())
            self.assertEqual(len({e['seq'] for e in data['events']}),60)
            self.assertEqual(data['current']['seq'],60)

    def test_family_workers_partition_jobs_and_active_phases_survive_other_events(self):
        from katarina.monitoring.activity_trace import read_activity
        with tempfile.TemporaryDirectory() as directory:
            trace=ActivityTrace(directory)
            trace.emit('GEMINI','STARTED')
            trace.emit('TEST_BREAKOUT','STARTED')
            for _ in range(85):trace.emit('HEARTBEAT','IDLE')
            self.assertEqual({e['phase'] for e in read_activity(directory)['active']},{'GEMINI','TEST_BREAKOUT'})
            trace.emit('CONNECT','STARTED');trace.emit('DEGRADED','FAILED')
            self.assertNotIn('CONNECT',{e['phase'] for e in read_activity(directory)['active']})
            trace.emit('TEST_BREAKOUT','DONE')
            self.assertEqual({e['phase'] for e in read_activity(directory)['active']},{'GEMINI'})
            trace.emit('STOPPED','DONE');self.assertEqual(read_activity(directory)['active'],[])
            self.assertEqual(sum(len([c for c in GRID if c[0]==f]) for f in ('MOMENTUM','MEAN_REVERSION','BREAKOUT')),len(GRID))

    def test_gemini_budget_persists_and_hypotheses_never_execute(self):
        from katarina.intelligence.lab.autonomous_research import ResearchPool
        class Model:
            def __init__(self):self.calls=0
            def complete(self,messages,**kwargs):self.calls+=1;return {'hypothesis':'public fixture'}
            def telemetry(self):return {'successful_calls':self.calls,'failed_calls':0}
        with tempfile.TemporaryDirectory() as directory:
            model=Model();pool=ResearchPool(directory,ActivityTrace(directory),model)
            self.assertTrue(pool.model_once());self.assertFalse(pool.model_once())
            restarted=ResearchPool(directory,ActivityTrace(directory),model)
            self.assertFalse(restarted.model_once());self.assertEqual(model.calls,1)
            with closing(sqlite3.connect(Path(directory)/'experiment-jobs.sqlite3')) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM gemini_hypotheses').fetchone()[0],1)
            self.assertFalse(json.loads((Path(directory)/'gemini-research.json').read_text())['live_authorized'])

    def test_twelve_research_workers_enter_work_concurrently(self):
        from katarina.intelligence.lab.autonomous_research import ResearchPool
        barrier=threading.Barrier(12);entered=set();guard=threading.Lock();ready=threading.Event();errors=[]
        def work(*args):
            with guard:
                entered.add(threading.current_thread().name)
                if len(entered)==12:ready.set()
            try:barrier.wait(timeout=5)
            except threading.BrokenBarrierError:errors.append('barrier broken')
            return False
        with tempfile.TemporaryDirectory() as directory:
            pool=ResearchPool(directory,ActivityTrace(directory))
            with patch.object(ResearchWorker,'tick',work),patch.object(ResearchPool,'review_one',work),patch.object(ResearchPool,'model_once',work):
                try:
                    pool.start();self.assertTrue(ready.wait(5))
                    self.assertEqual(pool.background_count,13)
                finally:pool.close()
            self.assertEqual(len(entered),12);self.assertEqual(errors,[])

    def test_nine_partitions_and_two_stress_reviews_are_distinct(self):
        from katarina.intelligence.lab.autonomous_research import ResearchPool
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with closing(sqlite3.connect(root/'context.sqlite3')) as db,db:
                setup(db);db.execute("INSERT INTO lab_universe(symbol) VALUES('FIXTURE')")
                db.executemany('INSERT INTO lab_bars VALUES(?,?,?,?,?,?)',[('FIXTURE',*r) for r in bars()])
                db.execute('INSERT INTO lab_runs VALUES(?,?,?,?,?)',('source','FIXTURE','2026-01-01','x',json.dumps({'spread_proxy_price':.01})))
            pool=ResearchPool(root,ActivityTrace(root))
            with patch('katarina.intelligence.lab.research_capacity.research_capacity',return_value={'status':'READY'}):
                for worker in pool.workers:self.assertTrue(worker.tick())
            with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db:
                rows=[json.loads(r[0]) for r in db.execute('SELECT result_json FROM trials')]
                self.assertEqual(len({(r['method'],r['horizon']) for r in rows}),9)
            self.assertTrue(pool.review_one(2));self.assertTrue(pool.review_one(3))
            with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db:
                reviews=[json.loads(r[0]) for r in db.execute('SELECT result_json FROM stress_reviews')]
                self.assertEqual({r['stress_cost_multiplier'] for r in reviews},{2,3})
                self.assertTrue(all(r['live_authorized'] is False for r in reviews))

    def test_exact_dataset_survives_cache_changes_and_repairs_legacy_review(self):
        from katarina.intelligence.lab.autonomous_research import ResearchPool, preserve_dataset
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=bars()
            with closing(sqlite3.connect(root/'context.sqlite3')) as db,db:
                setup(db);db.execute("INSERT INTO lab_universe(symbol) VALUES('FIXTURE')")
                db.executemany('INSERT INTO lab_bars VALUES(?,?,?,?,?,?)',[('FIXTURE',*r) for r in source])
                db.execute('INSERT INTO lab_runs VALUES(?,?,?,?,?)',('source','FIXTURE','2026-01-01','x',json.dumps({'spread_proxy_price':.01})))
            trace=ActivityTrace(root);pool=ResearchPool(root,trace)
            with patch('katarina.intelligence.lab.research_capacity.research_capacity',return_value={'status':'READY'}):
                self.assertTrue(ResearchWorker(root,trace).tick())
            with closing(sqlite3.connect(root/'context.sqlite3')) as db,db:
                db.execute('UPDATE lab_bars SET c=c+10')
            self.assertTrue(pool.review_one(2))
            with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db,db:
                review=json.loads(db.execute('SELECT result_json FROM stress_reviews').fetchone()[0])
                self.assertEqual(review['dataset_source'],'FROZEN_EXPERIMENT_SNAPSHOT')
                self.assertNotEqual(review['status'],'DATASET_CHANGED_REVIEW_UNAVAILABLE')
                db.execute("UPDATE stress_reviews SET result_json=?",(json.dumps({'status':'DATASET_CHANGED_REVIEW_UNAVAILABLE','live_authorized':False}),))
                digest=db.execute('SELECT digest FROM trials').fetchone()[0]
                db.execute('DELETE FROM research_datasets')
            self.assertFalse(pool.repair_one())
            with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db,db:preserve_dataset(db,digest,source)
            self.assertTrue(pool.repair_one());self.assertFalse(pool.repair_one())
            with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db:
                repaired=json.loads(db.execute('SELECT result_json FROM stress_reviews').fetchone()[0])
                self.assertEqual(repaired['recovered_from'],'DATASET_CHANGED_REVIEW_UNAVAILABLE')
                self.assertFalse(repaired['live_authorized'])
                self.assertEqual(db.execute('SELECT COUNT(*) FROM research_repairs').fetchone()[0],1)

    def test_gemini_failure_persists_retry_instead_of_started(self):
        from katarina.intelligence.lab.autonomous_research import ResearchPool
        class FailingModel:
            def complete(self,*args,**kwargs):raise RuntimeError('PRIVATE_PROVIDER_BODY')
            def telemetry(self):return {'successful_calls':0,'failed_calls':1}
        with tempfile.TemporaryDirectory() as directory:
            pool=ResearchPool(directory,ActivityTrace(directory),FailingModel())
            self.assertTrue(pool.model_once());self.assertFalse(pool.model_once())
            raw=Path(directory,'gemini-research.json').read_text()
            self.assertEqual(json.loads(raw)['status'],'RETRY_AFTER_COOLDOWN')
            self.assertNotIn('PRIVATE',raw)
