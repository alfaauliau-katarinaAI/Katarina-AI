"""One bounded maintenance worker; Gemini advises, never executes repairs."""
from katarina.monitoring.snapshot_io import replace_snapshot
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
import time

from katarina.memory.store import MemoryStore


class NetworkDoctor:
    def __init__(self, root, trace, pool=None, model=None, clock=time.time):
        self.root=Path(root);self.trace=trace;self.pool=pool;self.model=model;self.clock=clock
        self.stop=threading.Event()
        self.thread=threading.Thread(target=self.run,name='network-doctor',daemon=True)
        self.state={'status':'STARTING','checks':0,'memory_records_added':0}
        self.path=self.root/'network-doctor.sqlite3'
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS progress(source TEXT PRIMARY KEY,cursor INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS budget(name TEXT PRIMARY KEY,last_attempt REAL NOT NULL)')

    def start(self):self.thread.start();return self

    def close(self):
        self.stop.set();self.thread.join(timeout=65)
        if self.thread.is_alive():raise RuntimeError('DOCTOR_STOP_TIMEOUT')

    def _read(self,path):
        return sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)

    def remember(self,memory):
        """Incremental trial archive plus idempotent final broker outcomes."""
        added=0
        sources=[('experiment-jobs.sqlite3','trials','result_json'),
                 ('context.sqlite3','sensor_recovery_attempts','report_json'),
                 ('calibration.sqlite3','calibration_runs','report_json'),
                 ('experiment-jobs.sqlite3','research_reports','report_json'),
                 ('experiment-jobs.sqlite3','stress_reviews','result_json'),
                 ('demo-forward/experiment.sqlite3','demo_variants','report_json'),
                 ('demo-forward/experiment.sqlite3','demo_policy_reviews','report_json')]
        for filename,table,column in sources:
            p=self.root/filename
            if not p.exists():continue
            source=filename+':'+table
            with closing(sqlite3.connect(self.path)) as progress:
                row=progress.execute('SELECT cursor FROM progress WHERE source=?',(source,)).fetchone()
            cursor=row[0] if row else 0
            with closing(self._read(p)) as db:
                if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():continue
                rows=db.execute(f'SELECT rowid,{column} FROM {table} WHERE rowid>? ORDER BY rowid LIMIT 20',(cursor,)).fetchall()
            for seq,raw in rows:
                if self.stop.is_set() or (self.root/'continuous.stop').exists():return added
                result=memory.append_operational_event('RESEARCH_TRIAL_ARCHIVE',{'source':source,'source_row':seq,'result':json.loads(raw)})
                added+=result.inserted
                with closing(sqlite3.connect(self.path)) as db,db:
                    db.execute('INSERT OR REPLACE INTO progress VALUES(?,?)',(source,seq))
        p=self.root/'demo-forward/orders.sqlite3'
        if p.exists():
            with closing(self._read(p)) as db:
                rows=db.execute("SELECT intent_id,outcome_json FROM demo_outbox WHERE state='CLOSED' AND outcome_json IS NOT NULL LIMIT 10000").fetchall()
            for ident,raw in rows:
                added+=memory.append_trade_experience({'scope':'DEMO','intent_id':ident,'outcome':json.loads(raw)}).inserted
        return added

    def _budget(self,name,seconds):
        with closing(sqlite3.connect(self.path)) as db,db:
            row=db.execute('SELECT last_attempt FROM budget WHERE name=?',(name,)).fetchone()
            if row and self.clock()-row[0]<seconds:return False
            db.execute('INSERT OR REPLACE INTO budget VALUES(?,?)',(name,self.clock()))
        return True

    def repair_threads(self):
        repairs=[]
        pool=self.pool
        if pool is None or pool.stop.is_set() or self.stop.is_set() or (self.root/'continuous.stop').exists():return repairs
        specs=[(pool,'thread',pool.run,()),(pool,'review_thread',pool.review_loop,(2,)),
               (pool,'stress_thread',pool.review_loop,(3,)),(pool,'model_thread',pool.model_loop,())]
        specs += [(w,'thread',w.run,()) for w in pool.workers if not w.stop.is_set()]
        for owner,field,target,args in specs:
            old=getattr(owner,field)
            if old.is_alive() or not self._budget('restart:'+old.name,300):continue
            replacement=threading.Thread(target=target,args=args,name=old.name,daemon=True)
            setattr(owner,field,replacement)
            replacement.start()
            repairs.append('RESTARTED_'+old.name)
        return repairs

    def check(self):
        issues=[];repairs=self.repair_threads()
        if self._budget('file_housekeeping',300):
            try:
                from katarina.intelligence.operations.file_housekeeping import organize
                housekeeping=organize(self.root)
                self.state['housekeeping']=housekeeping
                self.trace.emit('MEMORY_WRITE','DONE',action='FILE_HOUSEKEEPING_CHECKED',count=housekeeping['moved'])
            except (OSError,ValueError):
                self.state['housekeeping']={'status':'RETRY_PENDING','scope':'HOUSEKEEPING_INBOX_ONLY'}

        for name,age in [('continuous-status.json',600),('latest.json',900),('demo-forward/status.json',600)]:
            p=self.root/name
            if not p.exists():issues.append('MISSING_'+name.replace('/','_'))
            elif self.clock()-p.stat().st_mtime>age:issues.append('STALE_'+name.replace('/','_'))
        if self.pool is not None:
            threads=[self.pool.thread,self.pool.review_thread,self.pool.stress_thread,self.pool.model_thread]+[w.thread for w in self.pool.workers]
            if any(not t.is_alive() for t in threads):issues.append('RESEARCH_THREAD_STOPPED_REQUIRES_REVIEW')
        calibration_path=self.root/'calibration.json'
        if calibration_path.exists():
            try:
                calibration=json.loads(calibration_path.read_text(encoding='utf-8'))
                if calibration.get('pid')==__import__('os').getpid():
                    self.state['calibration']={k:calibration.get(k) for k in ('status','symbol','runs','verified_windows')}
                    if calibration.get('status')=='CONFLICTING_WINDOW_EVIDENCE':issues.append('CALIBRATION_CONFLICT_REQUIRES_REVIEW')
                    elif calibration.get('status') in ('MORE_BROKER_EVIDENCE_REQUIRED','AMBIGUOUS_WINDOW_ALIGNMENT'):issues.append('CALIBRATION_NEEDS_MORE_EVIDENCE')
            except (OSError,ValueError,TypeError):issues.append('CALIBRATION_STATUS_UNREADABLE')
        with MemoryStore(self.root/'cognitive-memory.sqlite3') as memory:
            memory._conn.execute('PRAGMA busy_timeout=2000')
            added=self.remember(memory)
            p=self.root/'context.sqlite3'
            if p.exists() and self._budget('gap_repair',300):
                # Reuse the existing deduplicated, bounded recovery queue. No
                # broker SDK calls, account changes, deletes or code rewriting.
                from katarina.intelligence.broker.data_recovery import setup, REASONS
                try:
                    cards=json.loads((self.root/'latest.json').read_text(encoding='utf-8')).get('symbols',{})
                except (OSError,ValueError):cards={}
                with closing(sqlite3.connect(p,timeout=2)) as db,db:
                    setup(db)
                    for symbol,card in cards.items():
                        if not isinstance(card,dict) or not card.get('sensor_reason'):continue
                        reason=card['sensor_reason'] if card['sensor_reason'] in REASONS else 'SENSOR_READ_FAILED'
                        db.execute("INSERT OR IGNORE INTO sensor_recovery(symbol,reason,status,updated_utc) VALUES(?,?,'PENDING',?)",(symbol,reason,datetime.now(timezone.utc).isoformat()))

                repairs.append('RECHECKED_DATA_GAP_QUEUE')
            if p.exists():
                with closing(self._read(p)) as db:
                    if db.execute("SELECT 1 FROM sqlite_master WHERE name='sensor_recovery'").fetchone():
                        if db.execute("SELECT COUNT(*) FROM sensor_recovery WHERE status!='VERIFIED'").fetchone()[0]:issues.append('DATA_GAPS_PENDING')
            if self._budget('integrity',1800):
                for name in ['context.sqlite3','experiment-jobs.sqlite3','demo-forward/orders.sqlite3']:
                    p=self.root/name
                    if p.exists():
                        with closing(self._read(p)) as db:
                            if db.execute('PRAGMA quick_check(1)').fetchone()[0]!='ok':issues.append('DATABASE_REQUIRES_REVIEW')
            report={'issues':issues,'repairs':repairs,'scope':'OPERATIONAL_HEALTH_NOT_MODEL_NEURONS','live_authorized':False}
            if issues or repairs:memory.append_operational_event('NETWORK_DOCTOR_CHECK',report)
            if issues and self.model is not None and not self.stop.is_set() and self._budget('gemini',600):
                self.trace.emit('GEMINI','STARTED',action='DOCTOR_DIAGNOSTIC_REVIEW')
                try:
                    reply=self.model.complete([{'role':'system','content':'Return JSON with diagnosis, evidence_needed, repair_proposal. Operational diagnostics only. No commands, code, orders, account data or credential requests. Suggestions require verification and never override owner stop or trading controls.'},{'role':'user','content':json.dumps(report)}],mode='fast')
                    memory.append_operational_event('DOCTOR_GEMINI_PROPOSAL',{'proposal':reply,'executed':False})
                    self.trace.emit('GEMINI','DONE',action='DOCTOR_PROPOSAL_SAVED_NOT_EXECUTED')
                except Exception:
                    issues.append('GEMINI_DIAGNOSTIC_UNAVAILABLE')
            self.state.update(status='REVIEW_REQUIRED' if issues else 'HEALTHY',issues=issues,
                              repairs=repairs,checks=self.state['checks']+1,
                              memory_records_added=self.state['memory_records_added']+added,
                              as_of_utc=datetime.now(timezone.utc).isoformat(),pid=__import__('os').getpid())
            tmp=self.root/'network-doctor.tmp';tmp.write_text(json.dumps(self.state)+'\n',encoding='utf-8');replace_snapshot(tmp,self.root/'network-doctor.json')
            if added:self.trace.emit('MEMORY_WRITE','DONE',action='DOCTOR_EVIDENCE_ARCHIVED',count=added)
        return self.state

    def run(self):
        while not self.stop.is_set() and not (self.root/'continuous.stop').exists():
            try:
                self.trace.emit('RECALL','STARTED',action='NETWORK_DOCTOR_CHECK')
                self.check()
                self.trace.emit('RECALL','DONE',action='NETWORK_DOCTOR_CHECK')
            except Exception as exc:
                self.state['error_type']=type(exc).__name__
                self.state.update(status='RETRY_PENDING',as_of_utc=datetime.now(timezone.utc).isoformat())
                tmp=self.root/'network-doctor.tmp'
                tmp.write_text(json.dumps(self.state)+'\n',encoding='utf-8');replace_snapshot(tmp,self.root/'network-doctor.json')
                self.trace.emit('RECALL','FAILED',action='DOCTOR_RETRY_PENDING')
            self.stop.wait(30)
