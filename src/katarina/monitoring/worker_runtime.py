"""Redacted facts from independently published worker and permission snapshots."""
from datetime import datetime,timezone
import json
from pathlib import Path
import re

PHASES=tuple('TEST_'+f+'_H'+str(h) for f in ('MOMENTUM','REVERSION','BREAKOUT') for h in (4,12,24))
STATES={'STARTING','EXPERIMENTING','EXPERIMENT_COMPLETED','WAITING_NEW_DATA','WAITING_DATA_OR_DATABASE','RETRY_PENDING','PAUSED_LOW_DISK','PAUSED_STORAGE_BUDGET'}


def _read(path):
    try:
        with path.open('rb') as f:raw=f.read(2_000_001)
        value=json.loads(raw) if len(raw)<=2_000_000 else {}
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError,TypeError):return {}


def _fresh(value,now,seconds=90,key='as_of_utc'):
    try:return -30<=(now-datetime.fromisoformat(value[key])).total_seconds()<=seconds
    except (KeyError,ValueError,TypeError):return False


def read_worker_runtime(root,pid,*,now=None):
    root=Path(root);now=now or datetime.now(timezone.utc)
    out=dict(status='OBSERVED',mode='AUTONOMOUS_PULL_AND_REPORT',workers=[],mt5_algo_enabled=None,
             demo_permission=None,demo_status='UNVERIFIED',live_authorized=False,
             as_of_utc=now.isoformat(),pid=pid)
    for i,phase in enumerate(PHASES,1):
        w=_read(root/('worker-'+phase+'.json'))
        fresh=w.get('pid')==pid and w.get('autonomous') is True and _fresh(w,now)
        out['workers'].append(dict(code='W'+str(i).zfill(2),phase=phase,
             status=w.get('status') if fresh and w.get('status') in STATES else 'UNVERIFIED',
             fresh=fresh,autonomous=fresh,completed=w.get('completed') if fresh and type(w.get('completed')) is int and w['completed']>=0 else None))
    evidence=_read(root/'latest.json');monitor=evidence.get('broker_account_monitor',{})
    if _fresh(evidence,now,180,'observed_at_utc') and isinstance(monitor,dict):
        flag=monitor.get('algo_trading_off')
        if type(flag) is bool:out['mt5_algo_enabled']=not flag
    demo=_read(root/'demo-forward/status.json');executor=_read(root/'demo-forward/executor.json')
    independent=executor.get('mode')=='DEMO' and executor.get('independent') is True and _fresh(executor,now)
    owner_pid=executor.get('pid') if independent else pid
    if demo.get('pid')==owner_pid and _fresh(demo,now):
        state=demo.get('status','')
        if isinstance(state,str) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',state):out['demo_status']=state
        if demo.get('execution_permission')=='DEMO_ORDER_PERMISSION_ON':
            out['demo_permission']=True;out['mt5_algo_enabled']=True
    if independent:
        out['executor']=dict(code='E01',pid=executor.get('pid'),independent=True,
            audit_only=executor.get('audit_only') is True,cycles=executor.get('cycles') if type(executor.get('cycles')) is int else 0,
            status=executor.get('status') if executor.get('status') in ('STARTING','RUNNING','AUDIT_ONLY','RETRY_PENDING','STOPPED') else 'UNVERIFIED',
            as_of_utc=executor.get('as_of_utc'))
    out['fresh_workers']=sum(w['fresh'] for w in out['workers'])
    out['paused_workers']=sum(w['status'].startswith('PAUSED_') for w in out['workers'])
    return out
