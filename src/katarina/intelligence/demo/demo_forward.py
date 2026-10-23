"""Single-owner demo research/forward loop, sharing the sensor terminal.

Actual SDK calls run only on the foreground owner thread. Research workers keep
their cached-data work. Historical candidates are re-tested with protective
exits; unqualified variants and missing signals do not create demonstration trades.
"""
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
import traceback

from katarina.engines.demo_execution import DemoExecutionBoundary, DemoIntent
from katarina.engines.risk import RiskGovernor
from katarina.intelligence.demo.demo_account import DemoAccountLedger, number
from katarina.intelligence.demo.demo_strategy import qualify_variant, signal, validate_rows, demo_policy, DEMO_POLICY


class DemoForwardRuntime:
    def __init__(self, root, config, *, trace=None, native=None, clock=time.time):
        if (getattr(config,'demo_experiments',False) is not True
                or config.priority!=('local',) or not config.terminal_path):
            raise ValueError('EXPLICIT_LOCAL_DEMO_CONFIGURATION_REQUIRED')
        self.root=Path(root);self.config=config;self.trace=trace;self.clock=clock
        self.private=self.root/'demo-forward';self.private.mkdir(exist_ok=True)
        self.native=native if native is not None else importlib.import_module('MetaTrader5')
        self.path=self.private/'experiment.sqlite3';self.last_step=-1e12
        self.gov=RiskGovernor.from_config(Path(__file__).resolve().parents[4]/'config/risk_governor_v2.json')
        self.boundary=DemoExecutionBoundary(self.native,self.gov,self.private/'orders.sqlite3',
            expected_login=config.expected_login,expected_server=config.expected_server,
            stop_requested=lambda:(self.root/'continuous.stop').exists() or (self.private/'demo.stop').exists(),clock=clock)
        with closing(self._db()) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS demo_variants(id TEXT PRIMARY KEY,trial_id TEXT,report_json TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS demo_entries(intent_id TEXT PRIMARY KEY,variant_id TEXT NOT NULL,signal_bar REAL NOT NULL,horizon INTEGER NOT NULL,result TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS demo_lessons(variant_id TEXT PRIMARY KEY,closed_count INTEGER NOT NULL,report_json TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS demo_candidate_visits(trial_id TEXT PRIMARY KEY,last_checked REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS demo_policy_reviews(id TEXT PRIMARY KEY,variant_id TEXT,policy TEXT,report_json TEXT NOT NULL)')
        self.status={}
        self.permission='UNVERIFIED'

    def _db(self):return sqlite3.connect(self.path,timeout=2)

    def _event(self, phase, state, action, count=0):
        if self.trace:self.trace.emit(phase,state,action=action,count=count)

    def _publish(self, state, **extra):
        with closing(self._db()) as db:
            counts=dict(db.execute('SELECT result,COUNT(*) FROM demo_entries GROUP BY result'))
            variants=db.execute('SELECT COUNT(*) FROM demo_variants').fetchone()[0]
        with closing(self.boundary._db()) as db:
            states=dict(db.execute('SELECT state,COUNT(*) FROM demo_outbox GROUP BY state'))
            outcomes=[json.loads(r[0]) for r in db.execute("SELECT outcome_json FROM demo_outbox WHERE state='CLOSED' AND outcome_json IS NOT NULL")]
        self.status=dict(schema_version=1,pid=os.getpid(),as_of_utc=datetime.fromtimestamp(self.clock(),timezone.utc).isoformat(),
                         status=state,variants_researched=variants,entry_decisions=sum(counts.values()),
                         broker_positions_open=states.get('OPEN',0),closed_outcomes=len(outcomes),
                         winning_outcomes=sum(x['net_profit_native']>0 for x in outcomes),
                         losing_outcomes=sum(x['net_profit_native']<0 for x in outcomes),
                         unresolved_submissions=sum(states.get(k,0) for k in ('RESERVED','SUBMITTING','UNKNOWN','ACCEPTED','PARTIAL','OWNERSHIP_REVIEW','PROTECTION_REVIEW')),
                         risk_scope='DEMO_ENROLMENT_EPOCH_NOT_LIFETIME',execution_permission=self.permission,
                         live_authorized=False,**extra)
        tmp=self.private/'status.tmp';tmp.write_text(json.dumps(self.status,allow_nan=False)+'\n',encoding='utf-8');replace_snapshot(tmp,self.private/'status.json')
        return self.status

    def _publish_position_telemetry(self):
        """Best-effort bound DEMO snapshot for the independent public monitor.

        This remains a read-only MT5 projection. Any missing broker evidence
        leaves the public projection unavailable; it must never delay or alter
        protective DEMO position management.
        """
        try:
            from katarina.intelligence.broker.broker_account_monitor import inspect_broker_account
            observed=datetime.fromtimestamp(self.clock(),timezone.utc)
            monitor=inspect_broker_account(self.native,observed_at_utc=observed)
            snapshot=monitor.get('position_snapshot') or {}
            expected=sha256((str(self.config.expected_login)+'|'+self.config.expected_server).encode()).hexdigest()
            if (monitor.get('connected') is not True
                    or monitor.get('account_mode')!='DEMO'
                    or monitor.get('positions_read_success') is not True
                    or monitor.get('orders_read_success') is not True
                    or snapshot.get('status')!='OBSERVED'
                    or snapshot.get('private_account_binding')!=expected
                    or self.boundary._identity_error()):
                return
            report=dict(schema_version=1,pid=os.getpid(),as_of_utc=observed.isoformat(),
                        mode='DEMO',live_authorized=False,monitor=monitor)
            path=self.private/'position-monitor.tmp'
            path.write_text(json.dumps(report,allow_nan=False)+'\n',encoding='utf-8')
            replace_snapshot(path,self.private/'position-monitor.json')
        except (OSError,ValueError,TypeError,AttributeError,RuntimeError,sqlite3.Error):
            # Position telemetry is optional; actual broker protection wins.
            return

    def _candidate(self):
        path=self.root/'experiment-jobs.sqlite3'
        if not path.exists():return None
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
            rows=db.execute("SELECT t.id,t.symbol,t.digest,t.result_json FROM trials t LEFT JOIN research_report_heads h ON h.trial_id=t.id LEFT JOIN research_reports r ON r.id=h.report_id WHERE json_extract(t.result_json,'$.status')='NEEDS_FORWARD_VALIDATION' AND json_extract(t.result_json,'$.dataset_preserved')=1 ORDER BY CASE WHEN r.decision='CANDIDATE_FORWARD' THEN 0 ELSE 1 END,t.created_utc DESC LIMIT 32").fetchall()
            if not rows:return None
            with closing(self._db()) as visits,visits:
                checked=dict(visits.execute('SELECT trial_id,last_checked FROM demo_candidate_visits'))
                row=min(rows,key=lambda r:checked.get(r[0],-1))
                visits.execute('INSERT OR REPLACE INTO demo_candidate_visits VALUES(?,?)',(row[0],self.clock()))
            ident,symbol,digest,raw=row;original=json.loads(raw)
            with closing(self._db()) as cache:
                cached=cache.execute('SELECT report_json FROM demo_variants WHERE trial_id=?',(ident,)).fetchone()
            if cached:
                return dict(trial_id=ident,symbol=symbol,config=original,variant=self._policy(json.loads(cached[0])))
            from katarina.intelligence.lab.autonomous_research import preserved_dataset
            frozen=preserved_dataset(db,digest)
            if frozen is None:raise ValueError('DEMO_FROZEN_DATASET_MISSING')
        # A version includes frozen data and current immutable candidate parameters.
        self._event('EXPERIMENT','STARTED','DEMO_PROTECTED_VARIANT_RESEARCH')
        variant=qualify_variant(frozen,original,spread=original['spread_proxy_price'],original_id=ident)
        with closing(self._db()) as db,db:
            db.execute('INSERT OR IGNORE INTO demo_variants VALUES(?,?,?)',(variant['id'],ident,json.dumps(variant,allow_nan=False)))
        self._event('EXPERIMENT','DONE','DEMO_PROTECTED_VARIANT_RESEARCH')
        return dict(trial_id=ident,symbol=symbol,config=original,variant=self._policy(variant))

    def _policy(self, variant):
        updated=demo_policy(variant)
        ident=sha256((variant['id']+'|'+DEMO_POLICY).encode()).hexdigest()
        with closing(self._db()) as db,db:
            db.execute('INSERT OR IGNORE INTO demo_policy_reviews VALUES(?,?,?,?)',
                       (ident,variant['id'],DEMO_POLICY,json.dumps(updated,allow_nan=False)))
        return updated

    def _clock_shift(self):
        raw=(self.root/'latest.json').read_bytes()
        if len(raw)>2_000_000:raise ValueError('DEMO_CLOCK_SNAPSHOT_TOO_LARGE')
        value=json.loads(raw);reference=value.get('time_reference') or {}
        stamp=datetime.fromisoformat(reference['observed_at_utc'])
        shift=reference.get('broker_server_shift_minutes')
        if (stamp.tzinfo is None or not 0<=self.clock()-stamp.timestamp()<=180
                or reference.get('canonical_market_clock')!='MT5_TICK_SERVER_TIME_CONVERTED_TO_UTC'
                or type(shift) is not int or not -720<=shift<=840
                or reference.get('confirming_symbols',0)<3):
            raise ValueError('DEMO_CURRENT_CLOCK_REFERENCE_UNVERIFIED')
        if shift % 60:raise ValueError('DEMO_CLOCK_SHIFT_NOT_INTEGER_HOUR')
        return shift//60

    def _quote(self, symbol):
        from katarina.intelligence.broker.causal_broker_quotes import last_past_quote
        quote=last_past_quote(self.native,symbol,datetime.fromtimestamp(self.clock(),timezone.utc),
                              server_shift_hours=self._clock_shift(),lookback_seconds=5)
        if quote is None or not 0<=self.clock()-quote[2]<=2:
            raise ValueError('DEMO_QUOTE_MISSING_OR_STALE')
        return quote

    def _filling(self, info):
        b=self.native;mask=getattr(info,'filling_mode',None)
        if type(mask) is not int:raise ValueError('DEMO_FILLING_UNVERIFIED')
        if mask&2:return b.ORDER_FILLING_IOC
        if mask&1:return b.ORDER_FILLING_FOK
        raise ValueError('DEMO_FILLING_UNSUPPORTED')

    def _manage(self):
        b=self.native
        with closing(self.boundary._db()) as db:
            rows=db.execute("SELECT intent_id,position_id,intent_json FROM demo_outbox WHERE state='OPEN'").fetchall()
        for ident,pid,raw in rows:
            with closing(self._db()) as db:
                entry=db.execute('SELECT horizon FROM demo_entries WHERE intent_id=?',(ident,)).fetchone()
            if entry is None:continue
            intent=json.loads(raw)
            if self.clock()<intent['created_at']+entry[0]*3600:continue
            quote=self._quote(intent['symbol']);info=b.symbol_info(intent['symbol'])
            if info is None:raise ValueError('DEMO_SYMBOL_SPEC_MISSING')
            self._event('SETTLE','STARTED','DEMO_HORIZON_CLOSE')
            receipt=self.boundary.close_owned(pid,price=quote[0] if intent['side']=='BUY' else quote[1],
                                              observed_at=quote[2],filling_mode=self._filling(info))
            self._event('SETTLE','DONE' if receipt['status']=='DEMO_CLOSE_ACCEPTED' else 'FAILED',receipt['status'])

    def _learn(self):
        with closing(self.boundary._db()) as orders:
            rows=orders.execute("SELECT intent_id,outcome_json FROM demo_outbox WHERE state='CLOSED' AND outcome_json IS NOT NULL LIMIT 10000").fetchall()
        groups={};updated=0
        with closing(self._db()) as db,db:
            for ident,raw in rows:
                entry=db.execute('SELECT variant_id FROM demo_entries WHERE intent_id=?',(ident,)).fetchone()
                if entry:groups.setdefault(entry[0],[]).append(json.loads(raw)['net_profit_native'])
            for ident,values in groups.items():
                old=db.execute('SELECT closed_count FROM demo_lessons WHERE variant_id=?',(ident,)).fetchone()
                if old and old[0]==len(values):continue
                report=dict(closed_count=len(values),net_profit_native=sum(values),
                            wins=sum(v>0 for v in values),losses=sum(v<0 for v in values),
                            decision='COOLDOWN_RESEARCH_REQUIRED' if len(values)>=3 and sum(values)<0 else 'FORWARD_EVIDENCE_ACCUMULATING',
                            sample_sufficiency_verified=False,live_authorized=False)
                db.execute('INSERT OR REPLACE INTO demo_lessons VALUES(?,?,?)',(ident,len(values),json.dumps(report,allow_nan=False)))
                updated+=1
        if updated:self._event('MEMORY_WRITE','DONE','DEMO_FORWARD_LESSON_SAVED',updated)

    def step(self, *, execute=True, force=False, already_connected=False):
        now=self.clock()
        if not force and now-self.last_step<15:return self.status
        self.last_step=now;b=self.native
        if self.boundary.stop_requested():return self._publish('OWNER_STOP_REQUEST')
        try:
            if not already_connected and not b.initialize(path=self.config.terminal_path,timeout=10000):
                return self._publish('DEMO_TERMINAL_UNAVAILABLE')
            self.permission='UNVERIFIED'
            reason=self.boundary._identity_error()
            if reason:return self._publish(reason)
            self.permission=self.boundary._guard() or 'DEMO_ORDER_PERMISSION_ON'
            self._event('RISK_AUDIT','STARTED','DEMO_ACCOUNT_RECONCILIATION')
            with closing(self._db()) as db:
                ledger=DemoAccountLedger(db,login=self.config.expected_login,server=self.config.expected_server,clock=self.clock)
                facts=ledger.capture(b)
            self._publish_position_telemetry()
            reconciled=self.boundary.reconcile()
            self._learn()
            self._event('RISK_AUDIT','DONE','DEMO_ACCOUNT_RECONCILIATION')
            if reconciled['closed']:
                self._event('SETTLE','DONE','DEMO_BROKER_OUTCOME_RECORDED',reconciled['closed'])
            if execute and facts['positions']:
                self._manage()
                return self._publish('DEMO_POSITION_MONITORING',risk_reconciled=True)
            if facts['positions'] or facts['orders']:
                return self._publish('DEMO_BOOK_BUSY',risk_reconciled=True)
            self._event('RECALL','STARTED','DEMO_CANDIDATE_REVIEW')
            candidate=self._candidate()
            self._event('RECALL','DONE','DEMO_CANDIDATE_REVIEW')
            if candidate is None:return self._publish('NO_FORWARD_CANDIDATE',risk_reconciled=True)
            variant=candidate['variant']
            if not variant['qualified']:return self._publish('PROTECTED_VARIANT_NOT_QUALIFIED',risk_reconciled=True,qualified_variant=False)
            with closing(self._db()) as db:
                lesson=db.execute('SELECT report_json FROM demo_lessons WHERE variant_id=?',(variant['id'],)).fetchone()
            if lesson and json.loads(lesson[0])['decision']=='COOLDOWN_RESEARCH_REQUIRED':
                return self._publish('DEMO_VARIANT_COOLDOWN_RESEARCH_REQUIRED',risk_reconciled=True)
            reason=self.boundary._guard()
            if reason:return self._publish(reason,risk_reconciled=True,qualified_variant=True)
            if not execute:return self._publish('DEMO_AUDIT_READY_NO_ORDER',risk_reconciled=True,qualified_variant=True)
            shift=self._clock_shift();symbol=candidate['symbol'];quote=self._quote(symbol)
            rates=b.copy_rates_from_pos(symbol,b.TIMEFRAME_H1,1,66)
            if rates is None:return self._publish('DEMO_CLOSED_BARS_UNAVAILABLE')
            bars=[[int(r['time'])-shift,float(r['open']),float(r['high']),float(r['low']),float(r['close'])] for r in rates]
            validate_rows(bars)
            bars=[r for r in bars if r[0]+3600<=quote[2]]
            if len(bars)<55 or not 0<=quote[2]-(bars[-1][0]+3600)<=180:
                return self._publish('WAIT_NEXT_CAUSAL_H1_ENTRY',risk_reconciled=True)
            config=candidate['config'];scale=signal(bars,len(bars)-1,config)
            if scale is None:return self._publish('WAIT_STRATEGY_SIGNAL',risk_reconciled=True)
            info=b.symbol_info(symbol)
            if info is None or not number(info.volume_min) or not 0<info.volume_min<=info.volume_max:
                return self._publish('DEMO_SYMBOL_SPEC_UNVERIFIED')
            side=1 if config['side']=='BUY' else -1;price=quote[1] if side==1 else quote[0]
            tick=getattr(info,'trade_tick_size',0)
            if not number(tick) or tick<=0:return self._publish('DEMO_PRICE_GRID_UNVERIFIED')
            stop=(math.floor((price-2*scale)/tick) if side==1 else math.ceil((price+2*scale)/tick))*tick
            target=(math.ceil((price+4*scale)/tick) if side==1 else math.floor((price-4*scale)/tick))*tick
            volume=info.volume_min
            order_type=b.ORDER_TYPE_BUY if side==1 else b.ORDER_TYPE_SELL
            loss=b.order_calc_profit(order_type,symbol,volume,price,stop)
            if not number(loss) or loss>=0:return self._publish('DEMO_LOSS_ESTIMATE_UNAVAILABLE')
            # Explicit stress reserve; not a claim that future slippage or fees
            # are known. The minimum lot must fit even after this reserve.
            stress=b.order_calc_profit(order_type,symbol,volume,price,price-side*max(quote[1]-quote[0],tick)*3)
            if not number(stress):return self._publish('DEMO_COST_RESERVE_UNAVAILABLE')
            reserve=max(-loss*.3,abs(stress))
            margin=b.order_calc_margin(order_type,symbol,volume,price)
            if not number(margin) or margin<0 or margin>facts['account'].margin_free*.5:
                return self._publish('DEMO_MARGIN_BUDGET_EXCEEDED')
            ident=sha256((variant['id']+':'+str(int(bars[-1][0]))).encode()).hexdigest()
            with closing(self._db()) as db:
                if db.execute('SELECT 1 FROM demo_entries WHERE intent_id=?',(ident,)).fetchone():
                    return self._publish('DEMO_SIGNAL_ALREADY_EVALUATED')
            # Refresh full account risk immediately before asking the boundary.
            with closing(self._db()) as db:
                facts=DemoAccountLedger(db,login=self.config.expected_login,server=self.config.expected_server,clock=self.clock).capture(b)
            if facts['positions'] or facts['orders']:return self._publish('DEMO_BOOK_CHANGED')
            if not 0<=self.clock()-quote[2]<=2:return self._publish('DEMO_QUOTE_EXPIRED_BEFORE_SUBMISSION')
            risk=replace(facts['risk'],expected_rr=abs(target-price)/abs(price-stop))
            intent=DemoIntent(ident,variant['id'],symbol,config['side'],volume,price,stop,target,self.clock(),reserve)
            self._event('EXPERIMENT','STARTED','DEMO_ENTRY_SUBMISSION')
            result=self.boundary.submit(intent,risk,risk_observed_at=facts['observed_at'],filling_mode=self._filling(info))
            with closing(self._db()) as db,db:
                db.execute('INSERT OR IGNORE INTO demo_entries VALUES(?,?,?,?,?)',(ident,variant['id'],bars[-1][0],config['horizon'],result['status']))
            self._event('EXPERIMENT','DONE' if result['status']=='DEMO_ACCEPTED' else 'FAILED',result['status'])
            return self._publish(result['status'],risk_reconciled=True)
        except Exception as exc:
            self._event('RISK_AUDIT','FAILED','DEMO_FORWARD_REQUIRES_REVIEW')
            frames=traceback.extract_tb(exc.__traceback__)
            frame=frames[-1] if frames else None
            return self._publish('DEMO_FORWARD_REQUIRES_REVIEW',
                error_type=type(exc).__name__ if type(exc).__module__=='builtins' else 'DEPENDENCY_ERROR',
                error_module=Path(frame.filename).name if frame else None,
                error_line=frame.lineno if frame else None)
        finally:
            if not already_connected:
                try:b.shutdown()
                except Exception:pass

from katarina.monitoring.snapshot_io import replace_snapshot
