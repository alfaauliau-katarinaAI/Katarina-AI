from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from katarina.intelligence.network_doctor import NetworkDoctor
from katarina.memory.store import MemoryStore

class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.events=[];self.trace=SimpleNamespace(emit=lambda *a,**k:self.events.append((a,k)))
        self.doc=NetworkDoctor(self.root,self.trace)
    def test_archive_restart_idempotency_and_outcome(self):
        with closing(sqlite3.connect(self.root/'experiment-jobs.sqlite3')) as db,db:
            db.execute('CREATE TABLE trials(id TEXT,result_json TEXT)');db.execute('INSERT INTO trials VALUES(?,?)',('trial',json.dumps({'status':'FAIL'})))
        (self.root/'demo-forward').mkdir()
        with closing(sqlite3.connect(self.root/'demo-forward/orders.sqlite3')) as db,db:
            db.execute('CREATE TABLE demo_outbox(intent_id TEXT,state TEXT,outcome_json TEXT)')
            db.execute('INSERT INTO demo_outbox VALUES(?,?,?)',('intent','CLOSED',json.dumps({'net_profit_native':-1})))
        with MemoryStore(self.root/'cognitive-memory.sqlite3') as memory:
            self.assertEqual(self.doc.remember(memory),2)
            restarted=NetworkDoctor(self.root,self.trace)
            self.assertEqual(restarted.remember(memory),0)
            self.assertEqual(len(memory.load_trade_experiences()),1)
            self.assertEqual(memory.load_operational_events()[0]['payload']['result']['status'],'FAIL')
    def test_advice_cannot_execute_and_budget_survives_restart(self):
        calls=[]
        model=SimpleNamespace(complete=lambda *a,**k:(calls.append(1) or {'repair_proposal':'delete all files'}))
        self.doc.model=model
        result=self.doc.check()
        self.assertEqual(result['status'],'REVIEW_REQUIRED')
        self.assertEqual(len(calls),1)
        restarted=NetworkDoctor(self.root,self.trace,model=model);restarted.check()
        self.assertEqual(len(calls),1)
        with MemoryStore(self.root/'cognitive-memory.sqlite3') as memory:
            proposal=memory.load_latest_operational_event('DOCTOR_GEMINI_PROPOSAL')
            self.assertFalse(proposal['payload']['executed'])
        self.assertTrue((self.root/'cognitive-memory.sqlite3').exists())
    def test_stop_prevents_worker_checks(self):
        (self.root/'continuous.stop').touch();self.doc.start();self.doc.thread.join(2)
        self.assertEqual(self.doc.state['checks'],0)
    def test_missing_data_queue_is_bounded_deduplicated(self):
        with closing(sqlite3.connect(self.root/'context.sqlite3')):pass
        (self.root/'latest.json').write_text(json.dumps({'symbols':{'TEST':{'sensor_reason':'stale_market_tick'}}}))
        self.doc.check()
        with closing(sqlite3.connect(self.root/'context.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT symbol,status,attempts FROM sensor_recovery').fetchall(),[('TEST','PENDING',0)])
        self.doc.check()
        with closing(sqlite3.connect(self.root/'context.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sensor_recovery').fetchone()[0],1)

    def test_doctor_restarts_only_dead_worker_and_honors_stop(self):
        import threading
        alive=threading.Event();finish=threading.Event()
        def worker():alive.set();finish.wait(2)
        old=threading.Thread(target=lambda:None,name='test-readonly-worker');old.start();old.join()
        running=SimpleNamespace(is_alive=lambda:True)
        pool=SimpleNamespace(stop=threading.Event(),thread=running,review_thread=running,stress_thread=running,model_thread=running,
                             run=lambda:None,review_loop=lambda x:None,model_loop=lambda:None,
                             workers=[SimpleNamespace(thread=old,run=worker,stop=threading.Event())])
        self.doc.pool=pool
        # Give fake healthy slots names; they are never restarted.
        running.name='healthy'
        self.assertEqual(self.doc.repair_threads(),['RESTARTED_test-readonly-worker'])
        self.assertTrue(alive.wait(1));self.assertEqual(self.doc.repair_threads(),[])
        finish.set();pool.workers[0].thread.join()
        self.assertEqual(self.doc.repair_threads(),[]) # restart budget survives dead replacement
        pool.stop.set();self.assertEqual(self.doc.repair_threads(),[])

    def test_calibration_conflict_is_reported_to_doctor(self):
        import os
        (self.root/'calibration.json').write_text(json.dumps({'pid':os.getpid(),'status':'CONFLICTING_WINDOW_EVIDENCE','symbol':'TEST','verified_windows':0}))
        result=self.doc.check()
        self.assertIn('CALIBRATION_CONFLICT_REQUIRES_REVIEW',result['issues'])
        self.assertEqual(result['calibration']['verified_windows'],0)
