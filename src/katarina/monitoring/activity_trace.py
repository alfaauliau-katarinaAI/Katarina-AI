"""Actual bounded lifecycle events written by the canonical observer, never simulated."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

PHASES = frozenset(('STARTING','CONNECT','NEWS','SENSORS','TECHNICAL','MEMORY',
                   'RISK_AUDIT','WAIT_ACK','PUBLISH','WAITING','DEGRADED','STOPPED','BLOCKED',
                   'SETTLE','CHECKPOINT','LEARNING_REVIEW','RESEARCH','MEMORY_WRITE','RECALL','ASSOCIATION'))
STATES = frozenset(('STARTED','DONE','FAILED','IDLE'))
FIELDS = ('symbol','method','market_state','action')

def clean_activity(value, *, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        pid, cycle, events = value['pid'], value['cycle'], value['events']
        if type(pid) is not int or pid <= 0 or type(cycle) is not int or cycle < 0:
            raise ValueError()
        output = []
        for event in events[-80:]:
            stamp = datetime.fromisoformat(event['at_utc'].replace('Z','+00:00'))
            if stamp.tzinfo is None or not -30 <= (now-stamp).total_seconds() <= 600:
                continue
            if event['phase'] not in PHASES or event['state'] not in STATES:
                continue
            if type(event['seq']) is not int or event['seq'] < 1:
                continue
            row = {k:event[k] for k in ('seq','at_utc','phase','state')}
            for key in FIELDS:
                field=event.get(key)
                if isinstance(field,str) and re.fullmatch(r'[A-Za-z0-9_.:#/-]{1,64}',field):
                    row[key]=field
            if type(event.get('count')) is int and 0 <= event['count'] <= 1000000:
                row['count']=event['count']
            output.append(row)
        current=output[-1] if output else None
        fresh=bool(current and -30 <= (now-datetime.fromisoformat(current['at_utc'].replace('Z','+00:00'))).total_seconds() <= 180)
        return dict(schema_version=1,pid=pid,cycle=cycle,current=current,
                    events=output,fresh=fresh,source='CANONICAL_OBSERVER_EVENTS')
    except (KeyError,TypeError,ValueError,AttributeError):
        return dict(schema_version=1,pid=None,cycle=None,current=None,
                    events=[],fresh=False,source='CANONICAL_OBSERVER_EVENTS')

class ActivityTrace:
    def __init__(self,root):
        self.root=Path(root)
        self.cycle=0
        self.events=[]
        self.seq=0

    def emit(self,phase,state,**values):
        if phase not in PHASES or state not in STATES:
            raise ValueError('invalid_activity_event')
        self.seq+=1
        event=dict(seq=self.seq,at_utc=datetime.now(timezone.utc).isoformat(),
                   phase=phase,state=state)
        for key in FIELDS+('count',):
            if key in values:
                event[key]=values[key]
        self.events=(self.events+[event])[-80:]
        data=clean_activity(dict(pid=os.getpid(),cycle=self.cycle,events=self.events))
        try:
            temp=self.root/'runtime-activity.tmp'
            temp.write_text(json.dumps(data,allow_nan=False)+'\n',encoding='utf-8')
            temp.replace(self.root/'runtime-activity.json')
            return True
        except OSError:
            # Monitoring failure cannot change broker policy or observation semantics.
            return False

def read_activity(root):
    try:
        value=json.loads((Path(root)/'runtime-activity.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        value={}
    return clean_activity(value)
