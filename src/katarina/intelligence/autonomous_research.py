"""Bounded cached-data research worker. No broker, model, network or order access."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import os
from katarina.monitoring.activity_trace import error_code
from katarina.intelligence.research_capacity import DB_TIMEOUT
from katarina.intelligence.session_gaps import GAP_POLICY, spans_long_gap
from katarina.monitoring.snapshot_io import replace_snapshot
import sqlite3
import threading
import zlib

GRID = tuple(product(('MOMENTUM','MEAN_REVERSION','BREAKOUT'), (1,-1), (12,24,48), (4,12,24), (.5,1.,1.5)))
VERSION = 'cached-entry-grid-v2'
# Report publishing runs heavy queries under the shared write lock; keep it sparse.
REPORT_INTERVAL_SECONDS = 30


def preserve_dataset(db, digest, rows):
    """Freeze exact experiment inputs once; shared digest avoids per-trial copies."""
    db.execute('CREATE TABLE IF NOT EXISTS research_datasets(digest TEXT PRIMARY KEY,rows_zlib BLOB NOT NULL)')
    if db.execute('SELECT 1 FROM research_datasets WHERE digest=?',(digest,)).fetchone():return
    payload=json.dumps(rows,separators=(',',':')).encode()
    if len(payload)>2_000_000 or sha256(payload).hexdigest()!=digest:
        raise ValueError('DATASET_INTEGRITY_FAILED')
    db.execute('INSERT OR IGNORE INTO research_datasets VALUES(?,?)',(digest,zlib.compress(payload)))


def preserved_dataset(db, digest):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_datasets'").fetchone():return None
    stored=db.execute('SELECT rows_zlib FROM research_datasets WHERE digest=?',(digest,)).fetchone()
    if stored is None:return None
    decoder=zlib.decompressobj();payload=decoder.decompress(stored[0],2_000_001)
    if len(payload)>2_000_000 or not decoder.eof or sha256(payload).hexdigest()!=digest:
        raise ValueError('DATASET_INTEGRITY_FAILED')
    rows=json.loads(payload)
    if not isinstance(rows,list) or not 512<=len(rows)<=8192:raise ValueError('DATASET_SHAPE_FAILED')
    return rows


def cost_review(rows, original, level):
    cfg=(original['method'],1 if original['side']=='BUY' else -1,original['lookback'],original['horizon'],original['threshold'])
    result=evaluate(rows,cfg,original['spread_proxy_price']*level,range_cost=.2*level)
    result['stress_cost_multiplier']=level
    return result


def evaluate(rows, config, spread, range_cost=.2):
    family, side, lookback, horizon, threshold = config
    split = len(rows)*2//3
    samples = [[], []]
    for i in range(max(lookback,14), len(rows)-horizon, horizon+1):
        prior = rows[i-lookback:i]
        scale = sum(r[2]-r[3] for r in rows[i-14:i])/14
        if scale <= 0: continue
        close = rows[i][4]
        signal = ((close-prior[0][4])*side > threshold*scale if family=='MOMENTUM' else
                  (sum(r[4] for r in prior)/lookback-close)*side > threshold*scale if family=='MEAN_REVERSION' else
                  close > max(r[2] for r in prior)+(threshold-.5)*scale if side==1 else
                  close < min(r[3] for r in prior)-(threshold-.5)*scale)
        if not signal: continue
        # Short daily pauses allowed; weekend/holiday/outage gaps still excluded.
        if spans_long_gap(rows,i,horizon): continue
        bucket = 0 if i+horizon < split else 1 if i >= split else None
        if bucket is not None:
            samples[bucket].append(((rows[i+horizon][4]-rows[i+1][1])*side-spread-range_cost*scale)/scale)
    def metrics(values):
        loss = -sum(x for x in values if x<0)
        return dict(n=len(values),mean_range_units=sum(values)/len(values) if values else None,
                    win_rate=sum(x>0 for x in values)/len(values) if values else None,
                    profit_factor=sum(x for x in values if x>0)/loss if loss else None)
    dev, review = map(metrics,samples)
    assessment=('INSUFFICIENT_SAMPLES' if min(dev['n'],review['n'])<30 else
                'REJECTED_IN_HISTORICAL_REVIEW' if dev['mean_range_units']<=0 or review['mean_range_units']<=0 else
                'NEEDS_FORWARD_VALIDATION')
    return dict(method=family,side='BUY' if side==1 else 'SELL',lookback=lookback,horizon=horizon,threshold=threshold,
                development=dev,review=review,review_is_chronological=True,independent_holdout=False,
                history_reused=True,execution_model='NEXT_H1_OPEN_FIXED_CLOSE_NO_SL_TP',gap_policy=GAP_POLICY,
                cost_model=f'RECORDED_CURRENT_SPREAD_PLUS_{range_cost:.2f}_MEAN_RANGE',
                status=assessment,live_authorized=False,improvement_verified=False)


class ResearchWorker:
    def __init__(self, root, trace, family=None, horizon=None):
        self.root=Path(root);self.trace=trace;self.stop=threading.Event()
        self.family=family
        self.horizon=horizon
        self.phase={None:"EXPERIMENT","MOMENTUM":"TEST_MOMENTUM","MEAN_REVERSION":"TEST_REVERSION","BREAKOUT":"TEST_BREAKOUT"}[family]
        if horizon is not None:self.phase += '_H'+str(horizon)
        self.thread=threading.Thread(target=self.run,name=self.phase.lower(),daemon=True)
        self.state={'status':'STARTING','completed':0,'live_authorized':False}

    def start(self):
        self.thread.start();return self

    def close(self):
        self.stop.set();self.thread.join(timeout=15)
        if self.thread.is_alive(): raise RuntimeError('RESEARCH_WORKER_STOP_TIMEOUT')

    def tick(self):
        from katarina.intelligence.research_capacity import research_capacity
        capacity=research_capacity(self.root)
        self.state['capacity']=capacity
        if capacity['status']!='READY':
            self.state['status']=capacity['status'];return False
        target=self.root/'experiment-jobs.sqlite3'
        with closing(sqlite3.connect(target,timeout=DB_TIMEOUT)) as jobs:
            jobs.execute('CREATE TABLE IF NOT EXISTS trials(id TEXT PRIMARY KEY,symbol TEXT,digest TEXT,created_utc TEXT,result_json TEXT)')
            jobs.execute("CREATE INDEX IF NOT EXISTS trials_role ON trials(json_extract(result_json,'$.method'),json_extract(result_json,'$.horizon'))")
            # A separate read-only connection; canonical observer retains exclusive broker ownership.
            with closing(sqlite3.connect((self.root/'context.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=2)) as data:
                symbols=data.execute('SELECT symbol FROM lab_universe ORDER BY symbol').fetchall()
                done=jobs.execute('SELECT COUNT(*) FROM trials').fetchone()[0]
                role_done=jobs.execute("SELECT COUNT(*) FROM trials WHERE json_extract(result_json,'$.method')=?",(self.family,)).fetchone()[0] if self.family else done
                if self.horizon is not None:
                    role_done=jobs.execute("SELECT COUNT(*) FROM trials WHERE json_extract(result_json,'$.method')=? AND json_extract(result_json,'$.horizon')=?",(self.family,self.horizon)).fetchone()[0]
                for offset in range(len(symbols)):
                    symbol=symbols[(done+offset)%len(symbols)][0]
                    rows=data.execute('SELECT stamp,o,h,l,c FROM lab_bars WHERE symbol=? ORDER BY stamp DESC LIMIT 8192',(symbol,)).fetchall()[::-1]
                    if len(rows)<512: continue
                    last=data.execute('SELECT result_json FROM lab_runs WHERE symbol=? ORDER BY created_utc DESC LIMIT 1',(symbol,)).fetchone()
                    if not last: continue
                    lab=json.loads(last[0])
                    # Instruments whose typical spread exceeds the cost gate are not tested.
                    if lab.get('cost_prohibitive') is True: continue
                    spread=lab.get('spread_proxy_price')
                    if not isinstance(spread,(int,float)) or spread<0: continue
                    digest=sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
                    for config in GRID:
                        if self.family is not None and config[0]!=self.family: continue
                        if self.horizon is not None and config[3]!=self.horizon: continue
                        if self.stop.is_set(): return False
                        ident=sha256(json.dumps([VERSION,symbol,digest,config,spread]).encode()).hexdigest()
                        if jobs.execute('SELECT 1 FROM trials WHERE id=?',(ident,)).fetchone(): continue
                        self.state.update(status='EXPERIMENTING',completed=role_done)
                        self.trace.emit(self.phase,'STARTED',action='AUTONOMOUS_CACHED_RESEARCH',method=config[0],symbol=symbol)
                        try:
                            result=evaluate(rows,config,spread)
                            result["spread_proxy_price"]=spread
                            result["spread_source"]=lab.get('spread_source','LEGACY_CURRENT_QUOTE')
                            # Two short write transactions instead of one long one.
                            with jobs:
                                preserve_dataset(jobs,digest,rows)
                            result['dataset_preserved']=True
                            with jobs:
                                jobs.execute('INSERT OR IGNORE INTO trials VALUES(?,?,?,?,?)',(ident,symbol,digest,datetime.now(timezone.utc).isoformat(),json.dumps(result,allow_nan=False)))
                        except Exception as exc:
                            self.state['last_error']=error_code(exc)
                            self.trace.emit(self.phase,'FAILED',action='AUTONOMOUS_CACHED_RESEARCH',symbol=symbol,error=error_code(exc))
                            raise
                        self.trace.emit(self.phase,'DONE',action='AUTONOMOUS_CACHED_RESEARCH',method=config[0],symbol=symbol,count=1)
                        self.state.update(status='EXPERIMENT_COMPLETED',completed=role_done+1)
                        return True
        self.state.update(status='WAITING_NEW_DATA',completed=role_done)
        return False

    def run(self):
        while not self.stop.is_set():
            try:
                worked=self.tick()
            except sqlite3.OperationalError:
                self.state['status']='WAITING_DATA_OR_DATABASE';worked=False
            except Exception:
                self.state['status']='RETRY_PENDING';worked=False
            payload=dict(self.state,pid=os.getpid(),autonomous=True,as_of_utc=datetime.now(timezone.utc).isoformat(),grid_size=len(GRID))
            try:
                name='multitask-status' if self.family is None else 'worker-'+self.phase
                temp=self.root/(name+'.tmp')
                temp.write_text(json.dumps(payload)+'\n',encoding='utf-8');replace_snapshot(temp,self.root/(name+'.json'))
            except OSError: pass
            # Bounded pace, no expensive model calls or busy looping when all jobs are exhausted.
            self.stop.wait(2 if worked else 10)


class ResearchPool:
    """Nine disjoint pattern/horizon experiments, two cost reviews and Gemini ideation."""
    def __init__(self,root,trace,model=None):
        self.root=Path(root);self.trace=trace;self.model=model
        self.stop=threading.Event();self.state={'status':'STARTING','completed':0,'live_authorized':False}
        self.workers=[ResearchWorker(root,trace,f,h) for f in ('MOMENTUM','MEAN_REVERSION','BREAKOUT') for h in (4,12,24)]
        self.review_thread=threading.Thread(target=self.review_loop,args=(2,),name='cost-stress-2x',daemon=True)
        self.stress_thread=threading.Thread(target=self.review_loop,args=(3,),name='cost-stress-3x',daemon=True)
        self.model_thread=threading.Thread(target=self.model_loop,name='gemini-hypotheses',daemon=True)
        self.thread=threading.Thread(target=self.run,name='research-coordinator',daemon=True)
        self.review_states={level:{'status':'STARTING','completed':0} for level in (2,3)}
        self.model_state={'status':'WAITING_BUDGET' if model is not None else 'NOT_CONFIGURED','successful_calls':0,'failed_calls':0}

    @property
    def background_count(self):
        return sum(t.is_alive() for t in [self.thread,self.review_thread,self.stress_thread,self.model_thread]+[w.thread for w in self.workers])

    def start(self):
        for w in self.workers:w.start()
        self.review_thread.start();self.stress_thread.start();self.model_thread.start();self.thread.start();return self

    def close(self):
        self.stop.set()
        for w in self.workers:w.stop.set()
        for t in [self.thread,self.review_thread,self.stress_thread,self.model_thread]+[w.thread for w in self.workers]:t.join(timeout=65)
        if self.background_count:raise RuntimeError('RESEARCH_POOL_STOP_TIMEOUT')

    def _publish_role(self,phase,state):
        payload=dict(state,pid=os.getpid(),phase=phase,autonomous=True,as_of_utc=datetime.now(timezone.utc).isoformat())
        try:
            temp=self.root/('worker-'+phase+'.tmp');temp.write_text(json.dumps(payload)+'\n',encoding='utf-8');replace_snapshot(temp,self.root/('worker-'+phase+'.json'))
        except OSError:pass

    def review_one(self, level=2):
        from katarina.intelligence.research_capacity import research_capacity
        capacity=research_capacity(self.root);state=self.review_states[level]
        if capacity['status']!='READY':
            state['status']=capacity['status'];return False
        phase="VALIDATE" if level==2 else "VALIDATE3"
        prefix="" if level==2 else "COST3:"
        with closing(sqlite3.connect(self.root/'experiment-jobs.sqlite3',timeout=DB_TIMEOUT)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS stress_reviews(trial_id TEXT PRIMARY KEY,created_utc TEXT,result_json TEXT)')
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='trials'").fetchone():return False
            frozen=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_datasets'").fetchone()
            priority="CASE WHEN json_extract(result_json,'$.status')='NEEDS_FORWARD_VALIDATION' THEN 0 ELSE 1 END,"
            if frozen:priority+='CASE WHEN t.digest IN (SELECT digest FROM research_datasets) THEN 0 ELSE 1 END,'
            trial=db.execute("SELECT id,symbol,digest,result_json FROM trials t WHERE json_extract(t.result_json,'$.status')='NEEDS_FORWARD_VALIDATION' AND NOT EXISTS (SELECT 1 FROM stress_reviews s WHERE s.trial_id=?||t.id) ORDER BY "+priority+'created_utc LIMIT 1',(prefix,)).fetchone()
            if not trial:state['status']='WAITING_ELIGIBLE_CANDIDATE';return False
            state['status']='REVIEWING';self._publish_role(phase,state)
            self.trace.emit(phase,'STARTED',action='COST_STRESS_'+str(level)+'X')
            original=json.loads(trial[3]);rows=preserved_dataset(db,trial[2]);source='FROZEN_EXPERIMENT_SNAPSHOT'
            if rows is None:
                with closing(sqlite3.connect((self.root/'context.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=2)) as data:
                    rows=data.execute('SELECT stamp,o,h,l,c FROM lab_bars WHERE symbol=? ORDER BY stamp DESC LIMIT 8192',(trial[1],)).fetchall()[::-1]
                if sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()!=trial[2]:rows=None
                source='CURRENT_CACHE_EXACT_MATCH'
            if rows is None:result={'status':'DATASET_CHANGED_REVIEW_UNAVAILABLE','live_authorized':False}
            else:
                result=cost_review(rows,original,level);result['dataset_source']=source
            with db:db.execute('INSERT OR IGNORE INTO stress_reviews VALUES(?,?,?)',(prefix+trial[0],datetime.now(timezone.utc).isoformat(),json.dumps(result,allow_nan=False)))
            self.trace.emit(phase,'DONE',count=1)
            state.update(status='REVIEW_COMPLETED',completed=state['completed']+1)
            return True

    def repair_one(self):
        """Retry a failed legacy review only when its exact original dataset exists."""
        from katarina.intelligence.research_capacity import research_capacity
        if research_capacity(self.root)['status']!='READY':return False
        with closing(sqlite3.connect(self.root/'experiment-jobs.sqlite3',timeout=DB_TIMEOUT)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS research_repairs(id TEXT PRIMARY KEY,created_utc TEXT,result_json TEXT)')
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_datasets'").fetchone():return False
            row=db.execute("SELECT s.trial_id,t.digest,t.result_json FROM stress_reviews s JOIN trials t ON t.id=CASE WHEN s.trial_id LIKE 'COST3:%' THEN substr(s.trial_id,7) ELSE s.trial_id END JOIN research_datasets d ON d.digest=t.digest WHERE json_extract(s.result_json,'$.status')='DATASET_CHANGED_REVIEW_UNAVAILABLE' AND json_extract(t.result_json,'$.status')='NEEDS_FORWARD_VALIDATION' ORDER BY s.created_utc LIMIT 1").fetchone()
            if row is None:return False
            rows=preserved_dataset(db,row[1]);original=json.loads(row[2])
            self.trace.emit('LEARNING_REVIEW','STARTED',action='REPAIR_EXACT_DATASET_REVIEW')
            result=cost_review(rows,original,3 if row[0].startswith('COST3:') else 2)
            result['dataset_source']='FROZEN_EXPERIMENT_SNAPSHOT';result['recovered_from']='DATASET_CHANGED_REVIEW_UNAVAILABLE'
            stamp=datetime.now(timezone.utc).isoformat()
            with db:
                db.execute('UPDATE stress_reviews SET result_json=? WHERE trial_id=?',(json.dumps(result,allow_nan=False),row[0]))
                db.execute('INSERT OR IGNORE INTO research_repairs VALUES(?,?,?)',(row[0],stamp,json.dumps({'action':'RESTORED_EXACT_DATASET_REVIEW','previous_status':'DATASET_CHANGED_REVIEW_UNAVAILABLE','new_status':result['status'],'live_authorized':False})))
            self.trace.emit('LEARNING_REVIEW','DONE',action='REPAIR_EXACT_DATASET_REVIEW',count=1)
            return True

    def review_loop(self,level=2):
        while not self.stop.is_set():
            try:worked=self.review_one(level)
            except Exception as exc:
                self.review_states[level].update(status='RETRY_PENDING',last_error=error_code(exc))
                self.trace.emit('VALIDATE' if level==2 else 'VALIDATE3','FAILED',action='RETRY_PENDING',error=error_code(exc));worked=False
            self._publish_role('VALIDATE' if level==2 else 'VALIDATE3',self.review_states[level])
            self.stop.wait(15 if worked else 30)

    def model_once(self):
        if self.model is None:return False
        from katarina.intelligence.research_capacity import research_capacity
        capacity=research_capacity(self.root)
        if capacity['status']!='READY':self.model_state['status']=capacity['status'];return False
        target=self.root/'gemini-research.json'
        try:
            old=json.loads(target.read_text())
            if (datetime.now(timezone.utc)-datetime.fromisoformat(old['attempt_utc'])).total_seconds()<300:return False
        except (OSError,ValueError,KeyError):pass
        stamp=datetime.now(timezone.utc).isoformat()
        # Persist attempt before API call: restarts cannot bypass the five-minute budget.
        target.write_text(json.dumps({'attempt_utc':stamp,'status':'STARTED'})+'\n')
        self.trace.emit('GEMINI','STARTED',action='PUBLIC_PATTERN_HYPOTHESES')
        try:
            with closing(sqlite3.connect(self.root/'experiment-jobs.sqlite3',timeout=DB_TIMEOUT)) as db:
                db.execute('CREATE TABLE IF NOT EXISTS gemini_hypotheses(created_utc TEXT PRIMARY KEY,result_json TEXT)')
                previous=db.execute('SELECT result_json FROM gemini_hypotheses ORDER BY created_utc DESC LIMIT 2').fetchall()
            topics=('pullback','liquidity sweep','breakout','trend continuation','range rejection','failed breakout')
            topic=topics[int(datetime.now(timezone.utc).timestamp()//300)%len(topics)]
            context=' Focus: '+topic+'. Avoid repeating these previous public hypotheses: '+json.dumps(previous)[:6000]
            reply=self.model.complete([{'role':'system','content':'You are a market research hypothesis writer. Return valid JSON only, at most 150 words. Do not provide orders, code, instrument-specific advice or claim validation.'},{'role':'user','content':'Propose ONE falsifiable entry-pattern hypothesis. Return exactly six short string fields: pattern, signal_definition, invalidation, required_data, failure_mode, validation_plan. Distinguish assumptions from evidence. This is research only.'+context}],mode='fast')
            target.write_text(json.dumps({'attempt_utc':stamp,'status':'HYPOTHESES_ONLY','hypotheses':reply,'live_authorized':False},allow_nan=False)+'\n')
            with closing(sqlite3.connect(self.root/'experiment-jobs.sqlite3',timeout=DB_TIMEOUT)) as db, db:
                db.execute('INSERT OR IGNORE INTO gemini_hypotheses VALUES(?,?)',(stamp,json.dumps(reply,allow_nan=False)))
            self.model_state.update(status='HYPOTHESES_SAVED' ,**self.model.telemetry())
            self.trace.emit('GEMINI','DONE',action='HYPOTHESES_REQUIRE_IMPLEMENTATION_AND_TESTS')
        except Exception as exc:
            self.model_state.update(status='RETRY_AFTER_COOLDOWN',last_error=error_code(exc),**self.model.telemetry())
            target.write_text(json.dumps({'attempt_utc':stamp,'status':'RETRY_AFTER_COOLDOWN','live_authorized':False})+'\n')
            self.trace.emit('GEMINI','FAILED',action='RETRY_AFTER_COOLDOWN',error=error_code(exc))
        return True

    def model_loop(self):
        while not self.stop.is_set():
            try:self.model_once()
            except Exception:self.model_state['status']='RETRY_AFTER_COOLDOWN'
            self._publish_role('GEMINI',self.model_state)
            self.stop.wait(5)

    def run(self):
        next_repair=0;next_reports=0
        while not self.stop.is_set():
            try:
                import time
                if time.monotonic()>=next_repair:
                    next_repair=time.monotonic()+30
                    try:self.repair_one()
                    except Exception as exc:
                        self.trace.emit('LEARNING_REVIEW','FAILED',action='REPAIR_RETRY_PENDING',error=error_code(exc))
                if time.monotonic()>=next_reports:
                    next_reports=time.monotonic()+REPORT_INTERVAL_SECONDS
                    try:
                        from katarina.intelligence.research_reports import publish_reports
                        publish_reports(self.root,self.trace)
                    except Exception as exc:self.trace.emit('REPORT','FAILED',action='REPORT_RETRY_PENDING',error=error_code(exc))
                with closing(sqlite3.connect(self.root/'experiment-jobs.sqlite3',timeout=DB_TIMEOUT)) as db:
                    count=db.execute('SELECT COUNT(*) FROM trials').fetchone()[0]
                    reviews=db.execute('SELECT COUNT(*) FROM stress_reviews').fetchone()[0]
                self.state.update(status='RUNNING',completed=count,stress_reviews=reviews,background_workers=self.background_count,
                                  research_workers=12,workers=[dict(w.state,role=w.family,phase=w.phase,horizon=w.horizon) for w in self.workers],gemini=dict(self.model_state))
                temp=self.root/'multitask-status.tmp';temp.write_text(json.dumps(dict(self.state,as_of_utc=datetime.now(timezone.utc).isoformat(),grid_size=len(GRID)))+'\n');replace_snapshot(temp,self.root/'multitask-status.json')
            except (sqlite3.Error,OSError):pass
            self.stop.wait(1)

