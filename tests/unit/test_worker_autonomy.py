from contextlib import closing
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from katarina.intelligence.autonomous_research import ResearchWorker

class WorkerAutonomyTests(unittest.TestCase):
    def test_research_worker_persists_without_a_coordinator_command(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with closing(sqlite3.connect(root/'context.sqlite3')) as db,db:
                db.execute('CREATE TABLE lab_universe(symbol TEXT)');db.execute("INSERT INTO lab_universe VALUES('TEST')")
                db.execute('CREATE TABLE lab_bars(symbol TEXT,stamp INTEGER,o REAL,h REAL,l REAL,c REAL)')
                db.executemany('INSERT INTO lab_bars VALUES(?,?,?,?,?,?)',[('TEST',i*3600,100+i*.1,102+i*.1,99+i*.1,101+i*.1) for i in range(600)])
                db.execute('CREATE TABLE lab_runs(symbol TEXT,created_utc TEXT,result_json TEXT)')
                db.execute('INSERT INTO lab_runs VALUES(?,?,?)',('TEST',datetime.now(timezone.utc).isoformat(),json.dumps({'spread_proxy_price':.1})))
            finished=threading.Event()
            class Trace:
                def emit(self,phase,state,**fields):
                    if state=='DONE':finished.set()
            worker=ResearchWorker(root,Trace(),'MOMENTUM',4).start()
            try:self.assertTrue(finished.wait(5),'worker did not advance independently')
            finally:worker.close()
            with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db:
                self.assertGreater(db.execute('SELECT COUNT(*) FROM trials').fetchone()[0],0)
