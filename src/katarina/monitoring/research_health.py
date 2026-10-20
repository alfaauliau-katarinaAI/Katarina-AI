"""Read-only scheduler evidence; no broker access or writes to research memory."""
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
import sqlite3,time
from katarina.intelligence.research_capacity import research_capacity
from katarina.monitoring.worker_runtime import _read,_fresh

_CACHE={}
SUPPORT_STATES={'STARTING','REVIEWING','REVIEW_COMPLETED','WAITING_ELIGIBLE_CANDIDATE','PAUSED_LOW_DISK','PAUSED_STORAGE_BUDGET','RETRY_PENDING','WAITING_BUDGET','NOT_CONFIGURED','HYPOTHESES_SAVED','RETRY_AFTER_COOLDOWN'}


def read_research_health(root,pid,*,allowed,now=None):
    if not allowed:return {'status':'NOT_ATTESTED'}
    root=Path(root);now=now or datetime.now(timezone.utc)
    out=dict(status='OBSERVED',pid=pid,as_of_utc=now.isoformat(),capacity=research_capacity(root),
             policy='BASELINE_ELIGIBLE_ONLY',review_interval_seconds=15,support=[])
    for phase in ('VALIDATE','VALIDATE3','GEMINI'):
        w=_read(root/('worker-'+phase+'.json'))
        fresh=w.get('pid')==pid and w.get('autonomous') is True and _fresh(w,now)
        out['support'].append(dict(phase=phase,fresh=fresh,status=w.get('status') if fresh and w.get('status') in SUPPORT_STATES else 'UNVERIFIED'))
    key=(str(root),pid);cached=_CACHE.get(key)
    if cached and time.monotonic()-cached[0]<15:
        out.update(cached[1]);return out
    metrics=dict(latest_experiment_utc=None,latest_hypothesis_utc=None,eligible_candidates=None,pending_cost2=None,pending_cost3=None)
    try:
        with closing(sqlite3.connect((root/'experiment-jobs.sqlite3').resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)) as db:
            db.execute('PRAGMA query_only=ON');deadline=time.monotonic()+1.5;db.set_progress_handler(lambda:int(time.monotonic()>deadline),10000);db.execute('BEGIN')
            metrics['latest_experiment_utc']=db.execute('SELECT MAX(created_utc) FROM trials').fetchone()[0]
            metrics['latest_hypothesis_utc']=db.execute('SELECT MAX(created_utc) FROM gemini_hypotheses').fetchone()[0]
            count,p2,p3=db.execute("SELECT COUNT(*),SUM(NOT EXISTS(SELECT 1 FROM stress_reviews s WHERE s.trial_id=t.id)),SUM(NOT EXISTS(SELECT 1 FROM stress_reviews s WHERE s.trial_id='COST3:'||t.id)) FROM trials t WHERE json_extract(t.result_json,'$.status')='NEEDS_FORWARD_VALIDATION'").fetchone()
            metrics.update(eligible_candidates=count,pending_cost2=p2 or 0,pending_cost3=p3 or 0)
    except (sqlite3.Error,OSError,ValueError):pass
    _CACHE[key]=(time.monotonic(),metrics)
    if len(_CACHE)>8:
        _CACHE.pop(next(iter(_CACHE)))
    out.update(metrics);return out
