"""Durable rule-based experiment decisions. No broker, model, orders or promotion."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sqlite3
import shutil

DECISIONS=('CANDIDATE_FORWARD','AWAITING_COST_REVIEWS','REJECTED','INSUFFICIENT_EVIDENCE','REVIEW_BLOCKED')
CHECKS=('PASSED','PENDING','REJECTED','INSUFFICIENT','BLOCKED')
METHODS=('MOMENTUM','MEAN_REVERSION','BREAKOUT')

def check(value):
    if value is None:return 'PENDING'
    if value.get('status')=='DATASET_CHANGED_REVIEW_UNAVAILABLE':return 'BLOCKED'
    metrics=[value.get(k,{}) for k in ('development','review')]
    if any(type(m.get('n')) is not int or m['n']<30 for m in metrics):return 'INSUFFICIENT'
    means=[m.get('mean_range_units') for m in metrics]
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in means):return 'BLOCKED'
    if any(v<=0 for v in means):return 'REJECTED'
    return 'PASSED' if value.get('status')=='NEEDS_FORWARD_VALIDATION' else 'BLOCKED'

def decision_report(trial_id, symbol, created_utc, original, reviews):
    if original.get('method') not in METHODS or original.get('side') not in ('BUY','SELL'):raise ValueError('INVALID_RESEARCH_METHOD')
    states=dict(zip(('historical','cost2','cost3'),[check(original),*(check(r) for r in reviews)]))
    values=set(states.values())
    decision=('REJECTED' if 'REJECTED' in values else 'INSUFFICIENT_EVIDENCE' if 'INSUFFICIENT' in values
              else 'REVIEW_BLOCKED' if 'BLOCKED' in values else 'AWAITING_COST_REVIEWS' if 'PENDING' in values else 'CANDIDATE_FORWARD')
    out=dict(trial_id=trial_id,experiment_utc=created_utc,method=original['method'],side=original['side'],
             instrument_id=sha256(str(symbol).encode()).hexdigest()[:24],decision=decision,checks=states,
             checks_passed=sum(v=='PASSED' for v in states.values()),checks_required=3,
             consensus='RULE_BASED_CHECKS_NOT_INDEPENDENT_VOTES',engine='PYTHON_H1_RESEARCH',
             live_authorized=False,production_approved=False,independent_holdout=False,
             prospective_validation=False,mt5_tester_verified=False)
    for key,allowed in [('lookback',(12,24,48)),('horizon',(4,12,24)),('threshold',(.5,1,1.5))]:
        if original.get(key) in allowed:out[key]=original[key]
    for name in ('development','review'):
        source=original.get(name,{})
        out[name]={}
        for key in ('n','mean_range_units'):
            value=source.get(key)
            if type(value) in (int,float) and math.isfinite(value) and abs(value)<100_000_000:out[name][key]=value
    return out


def prepare_report_indexes(db):
    db.execute('CREATE INDEX IF NOT EXISTS research_heads_report_id ON research_report_heads(report_id)')
    db.execute('CREATE INDEX IF NOT EXISTS research_reports_created ON research_reports(created_utc DESC,id DESC)')
    db.execute('CREATE INDEX IF NOT EXISTS research_reports_decision_created ON research_reports(decision,created_utc DESC,id DESC)')
    db.execute('CREATE INDEX IF NOT EXISTS research_reports_head_counts ON research_reports(id,decision)')


def publish_reports(root, trace=None, batch=64):
    root=Path(root);stamp=datetime.now(timezone.utc).isoformat()
    target=root/'experiment-jobs.sqlite3'
    if shutil.disk_usage(root).free<2*1024**3 or (target.exists() and target.stat().st_size>320*1024**2):return 0
    with closing(sqlite3.connect(root/'experiment-jobs.sqlite3',timeout=2)) as db:
        db.execute('CREATE TABLE IF NOT EXISTS research_reports(id TEXT PRIMARY KEY,trial_id TEXT,created_utc TEXT,decision TEXT,report_json TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS research_report_heads(trial_id TEXT PRIMARY KEY,signature TEXT,report_id TEXT)')
        prepare_report_indexes(db)
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'trials','stress_reviews'}<=tables:return 0
        fields=('status','development.n','review.n','development.mean_range_units','review.mean_range_units')
        signature="||'|'||".join(f"coalesce(CAST(json_extract({alias}.result_json,'$.{field}') AS TEXT),'MISSING')" for alias in ('t','s2','s3') for field in fields)
        rows=db.execute(f"SELECT t.id,t.symbol,t.created_utc,t.result_json,s2.result_json,s3.result_json,{signature} FROM trials t LEFT JOIN stress_reviews s2 ON s2.trial_id=t.id LEFT JOIN stress_reviews s3 ON s3.trial_id='COST3:'||t.id LEFT JOIN research_report_heads h ON h.trial_id=t.id WHERE h.trial_id IS NULL OR h.signature!=({signature}) ORDER BY CASE WHEN json_extract(t.result_json,'$.status')='NEEDS_FORWARD_VALIDATION' THEN 0 ELSE 1 END,t.created_utc DESC LIMIT ?",(batch,)).fetchall()
        if rows and trace:trace.emit('REPORT','STARTED',action='EVIDENCE_DECISION_REPORT')
        with db:
            for ident,symbol,created,raw,r2,r3,version in rows:
                result=decision_report(ident,symbol,created,json.loads(raw),[json.loads(v) if v else None for v in (r2,r3)])
                report_id=sha256((ident+'|'+version).encode()).hexdigest()
                result.update(id=report_id,reported_utc=stamp)
                db.execute('INSERT OR IGNORE INTO research_reports VALUES(?,?,?,?,?)',(report_id,ident,stamp,result['decision'],json.dumps(result,allow_nan=False)))
                db.execute('INSERT OR REPLACE INTO research_report_heads VALUES(?,?,?)',(ident,version,report_id))
        if rows and trace:trace.emit('REPORT','DONE',action='EVIDENCE_DECISION_REPORT',count=len(rows))
        join='FROM research_report_heads h JOIN research_reports r ON r.id=h.report_id'
        recent=[json.loads(r[0]) for r in db.execute('SELECT r.report_json '+join+' ORDER BY r.created_utc DESC,r.rowid DESC LIMIT 8')]
        candidates=[json.loads(r[0]) for r in db.execute("SELECT r.report_json "+join+" WHERE r.decision IN ('CANDIDATE_FORWARD','AWAITING_COST_REVIEWS') ORDER BY r.created_utc DESC,r.rowid DESC LIMIT 3")]
        counts={k:0 for k in DECISIONS}
        counts.update(dict(db.execute('SELECT r.decision,COUNT(*) '+join+' GROUP BY r.decision')))
        total=db.execute('SELECT COUNT(*) FROM trials').fetchone()[0]
        value=dict(schema_version=1,status='RESEARCH_REPORTS',source='PERSISTED_RULE_BASED_RESEARCH_REPORTS',pid=os.getpid(),as_of_utc=stamp,
                   reviewed_experiments=sum(counts.values()),unreported_experiments=max(0,total-sum(counts.values())),counts=counts,
                   recent=recent,candidates=candidates,live_authorized=False,production_approved=False)
        temporary=root/'research-reports.tmp';temporary.write_text(json.dumps(value,allow_nan=False)+'\n',encoding='utf-8');temporary.replace(root/'research-reports.json')
        return len(rows)


def read_reports(root, pid):
    """Observe durable report records without relabelling their creation time.

    A report belongs to its dataset, not to the process that happened to render
    the previous JSON file. Re-observe persisted heads read-only after restart.
    """
    import time
    if type(pid) is not int or pid <= 0:
        return {'status':'NOT_ATTESTED'}
    root=Path(root)
    try:
        target=(root/'experiment-jobs.sqlite3').resolve()
        with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True,timeout=.25)) as db:
            db.execute('PRAGMA query_only=ON')
            deadline=time.monotonic()+2
            db.set_progress_handler(lambda: int(time.monotonic()>deadline),10000)
            db.execute('BEGIN')
            join='FROM research_report_heads h JOIN research_reports r ON r.id=h.report_id'
            recent=[json.loads(r[0]) for r in db.execute('SELECT r.report_json FROM research_reports r INDEXED BY research_reports_created WHERE EXISTS(SELECT 1 FROM research_report_heads h WHERE h.report_id=r.id) ORDER BY r.created_utc DESC,r.id DESC LIMIT 8')]
            candidates=[json.loads(r[0]) for r in db.execute("SELECT r.report_json FROM research_reports r INDEXED BY research_reports_decision_created WHERE r.decision IN ('CANDIDATE_FORWARD','AWAITING_COST_REVIEWS') AND EXISTS(SELECT 1 FROM research_report_heads h WHERE h.report_id=r.id) ORDER BY r.created_utc DESC,r.id DESC LIMIT 3")]
            counts={k:0 for k in DECISIONS}
            counts.update(dict(db.execute('SELECT r.decision,COUNT(*) FROM research_report_heads h JOIN research_reports r INDEXED BY research_reports_head_counts ON r.id=h.report_id GROUP BY r.decision')))
            total=db.execute('SELECT COUNT(*) FROM trials').fetchone()[0]
            latest=recent[0]['reported_utc'] if recent else None
            return dict(schema_version=1,status='RESEARCH_REPORTS',source='PERSISTED_RULE_BASED_RESEARCH_REPORTS',
                snapshot_role='READONLY_REPORT_OBSERVATION',pid=pid,as_of_utc=datetime.now(timezone.utc).isoformat(),
                latest_report_utc=latest,reviewed_experiments=sum(counts.values()),
                unreported_experiments=max(0,total-sum(counts.values())),counts=counts,
                recent=recent,candidates=candidates,live_authorized=False,production_approved=False)
    except (sqlite3.Error,OSError,ValueError,KeyError,TypeError):
        # Immutable reports remain inspectable while live DB observation is busy.
        # Keep the original creation time; only the file verification time is new.
        try:
            raw=(root/'research-reports.json').read_bytes()
            if len(raw)>32768:raise ValueError()
            cached=json.loads(raw)
            stamp=datetime.fromisoformat(cached['as_of_utc'])
            if (cached.get('status')!='RESEARCH_REPORTS' or stamp.tzinfo is None
                    or (datetime.now(timezone.utc)-stamp).total_seconds() < -30):raise ValueError()
            cached['producer_pid']=cached.get('pid')
            cached.update(pid=pid,snapshot_role='PERSISTED_REPORT_FILE_OBSERVATION',
                          latest_report_utc=cached['as_of_utc'],
                          as_of_utc=datetime.now(timezone.utc).isoformat(),
                          live_authorized=False,production_approved=False)
            return cached
        except (OSError,ValueError,KeyError,TypeError):
            return {'status':'NOT_ATTESTED'}
