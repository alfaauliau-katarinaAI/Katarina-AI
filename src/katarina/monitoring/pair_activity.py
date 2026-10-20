"""Pair identifiers and lifecycle timestamps only; never quotes or account fields."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re

PHASES={'SENSORS','HISTORY','TECHNICAL','VALIDATE','VALIDATE3'}|{
    'TEST_'+family+'_H'+str(h) for family in ('MOMENTUM','REVERSION','BREAKOUT') for h in (4,12,24)}
STATES={'STARTED','DONE','FAILED','IDLE'}


def _read(path):
    try:
        with path.open('rb') as f:raw=f.read(2_000_001)
        v=json.loads(raw) if len(raw)<=2_000_000 else {}
        return v if isinstance(v,dict) else {}
    except (OSError,ValueError,TypeError):return {}


def _fresh(stamp,now,seconds=180):
    try:
        t=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        return t.tzinfo is not None and -30<=(now-t).total_seconds()<=seconds
    except (AttributeError,ValueError,TypeError):return False


def symbol(value):
    return value if isinstance(value,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.#-]{0,31}',value) else None


def read_pair_activity(root,pid,*,allowed,now=None):
    empty={'status':'NOT_ATTESTED','symbols':[],'events':[],'active':[]}
    if not allowed or type(pid) is not int or pid<=0:return empty
    root=Path(root);now=now or datetime.now(timezone.utc);raw=_read(root/'runtime-activity.json')
    events=raw.get('events',[])
    if raw.get('pid')!=pid or not isinstance(events,list) or not events or not isinstance(events[-1],dict) or not _fresh(events[-1].get('at_utc'),now):return empty
    def clean(e):
        if not isinstance(e,dict):return None
        pair=symbol(e.get('symbol'))
        if not pair or e.get('phase') not in PHASES or e.get('state') not in STATES or type(e.get('seq')) is not int or not 1<=e['seq']<=1000000 or not _fresh(e.get('at_utc'),now):return None
        return {k:e[k] for k in ('symbol','phase','state','seq','at_utc')}
    rows=[c for e in events[-80:] if (c:=clean(e))]
    active=[c for e in raw.get('active',[])[:24] if (c:=clean(e)) and c['state']=='STARTED'] if isinstance(raw.get('active',[]),list) else []
    latest=_read(root/'latest.json');cards=latest.get('symbols',{})
    scanned=sorted(s for s,c in cards.items() if symbol(s) and isinstance(c,dict))[:64] if isinstance(cards,dict) and _fresh(latest.get('observed_at_utc'),now) else []
    names=sorted(set(scanned)|{e['symbol'] for e in rows+active})[:64]
    return dict(status='OBSERVED',pid=pid,as_of_utc=now.isoformat(),symbols=names,
                scan_observation_utc=latest.get('observed_at_utc') if scanned else None,
                events=rows,active=active,source='VPS_PAIR_LIFECYCLE',prices_included=False)
