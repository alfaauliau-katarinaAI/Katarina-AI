"""Public aggregate counters only; source data and per-instrument research stay private."""
from datetime import datetime, timezone
import json
import math
from katarina.monitoring.activity_trace import RESEARCH_PHASES
from pathlib import Path

COUNTERS=('universe_count','scanned_count','history_symbols','history_bars','experiments','strategy_candidates')
def clean_lab_status(value):
    if not isinstance(value,dict) or value.get('status') not in ('RUNNING','EMPTY_UNIVERSE','PAUSED_LOW_DISK','PAUSED_STORAGE_BUDGET'):
        return {'status':'NOT_ATTESTED'}
    out={k:value.get(k) if type(value.get(k)) is int and 0<=value[k]<=100000000 else None for k in COUNTERS}
    out.update(status=value['status'],live_authorized=False,improvement_verified=False,
               independent_holdout=False,broker_fill_verified=False)
    out['results']=[]
    for item in value.get('recent',[])[:6]:
        result=item.get('result',{}) if isinstance(item,dict) else {}
        choice=result.get('selected')
        if not isinstance(choice,dict) or choice.get('method') not in ('MOMENTUM','MEAN_REVERSION','BREAKOUT') or choice.get('side') not in ('BUY','SELL'): continue
        row={k:choice[k] for k in ('method','side')}
        for key in ('development_n','review_n','development_mean_r','review_mean_r','development_t','review_t'):
            v=choice.get(key);row[key]=round(v,6) if type(v) in (int,float) and math.isfinite(v) and abs(v)<1000000 else None
        verdict=(result.get('verdict') or {}).get('result') if isinstance(result.get('verdict'),dict) else None
        row['verdict']=verdict if verdict in ('PASSED_PRECOMMITTED_RULE','REJECTED','INSUFFICIENT_SAMPLES') else None
        out['results'].append(row)
    return out

def read_lab_status(root):
    try:
        raw=(Path(root)/'research-lab.json').read_bytes()
        if len(raw)>131072: raise ValueError()
        value=json.loads(raw)
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(value['as_of_utc'])).total_seconds()
        baseline_fresh=-30<=age<=180
        worker={}
        try:
            worker=json.loads((Path(root)/'multitask-status.json').read_text(encoding='utf-8'))
            worker_age=(datetime.now(timezone.utc)-datetime.fromisoformat(worker['as_of_utc'])).total_seconds()
            if not -30<=worker_age<=60:worker={}
        except (OSError,ValueError,TypeError,KeyError):pass
        if not baseline_fresh and not worker:raise ValueError()
        out=clean_lab_status(value)
        if not baseline_fresh:out['results']=[]
        try:
            worker=json.loads((Path(root)/'multitask-status.json').read_text(encoding='utf-8'))
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(worker['as_of_utc'])).total_seconds()
            count=worker.get('completed')
            if -30<=age<=60 and type(count) is int and 0<=count<=10000000:
                # Grid trials are individual experiments, unlike six-candidate baseline runs.
                roles={'MOMENTUM':'TEST_MOMENTUM','MEAN_REVERSION':'TEST_REVERSION','BREAKOUT':'TEST_BREAKOUT'}
                out['worker_phases']=[w.get('phase',roles.get(w.get('role'))) for w in worker.get('workers',[]) if isinstance(w,dict) and w.get('phase',roles.get(w.get('role'))) in RESEARCH_PHASES]
                if worker.get('background_workers',0)>0:out['worker_phases'].extend(['VALIDATE','VALIDATE3'] if worker.get('research_workers')==12 else ['VALIDATE'])
                if worker.get('gemini',{}).get('status') not in (None,'NOT_CONFIGURED'):out['worker_phases'].append('GEMINI')
                if type(out.get('experiments')) is int: out['experiments']+=count
                if type(out.get('strategy_candidates')) is int: out['strategy_candidates']+=count
        except (OSError,ValueError,TypeError,KeyError): pass
        return out
    except (OSError,ValueError,TypeError,KeyError): return {'status':'NOT_ATTESTED'}
