"""Actual bounded lifecycle events written by the canonical observer, never simulated."""
from katarina.monitoring.snapshot_io import replace_snapshot
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import threading

RESEARCH_PHASES = frozenset('TEST_'+f+'_H'+str(h) for f in ('MOMENTUM','REVERSION','BREAKOUT') for h in (4,12,24)) | frozenset(('TEST_MOMENTUM','TEST_REVERSION','TEST_BREAKOUT','VALIDATE','VALIDATE3','GEMINI','REPORT'))
PHASES = frozenset(('STARTING','CONNECT','NEWS','SENSORS','TECHNICAL','MEMORY',
                   'RISK_AUDIT','WAIT_ACK','PUBLISH','WAITING','DEGRADED','STOPPED','BLOCKED',
                   'SETTLE','CHECKPOINT','LEARNING_REVIEW','RESEARCH','MEMORY_WRITE','RECALL','ASSOCIATION','HISTORY','EXPERIMENT','HEARTBEAT','TEST_MOMENTUM','TEST_REVERSION','TEST_BREAKOUT','VALIDATE','GEMINI')) | RESEARCH_PHASES
STATES = frozenset(('STARTED','DONE','FAILED','IDLE'))
FIELDS = ('symbol','method','market_state','action','error')


def error_code(exc):
    """Short public failure class; never the message text, paths or account data."""
    name=type(exc).__name__
    text=str(exc).lower()
    if 'locked' in text:return name+':locked'
    if 'busy' in text:return name+':busy'
    return name

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
        active=[]
        for event in value.get('active',[])[:24]:
            try:
                stamp=datetime.fromisoformat(event['at_utc'].replace('Z','+00:00'))
                if (event['phase'] in PHASES and event['state']=='STARTED'
                        and type(event['seq']) is int and event['seq']>0 and stamp.tzinfo is not None
                        and -30<=(now-stamp).total_seconds()<=180):
                    active.append({k:event[k] for k in ('seq','at_utc','phase','state')})
            except (KeyError,TypeError,ValueError):pass
        current=output[-1] if output else None
        fresh=bool(current and -30 <= (now-datetime.fromisoformat(current['at_utc'].replace('Z','+00:00'))).total_seconds() <= 180)
        return dict(schema_version=1,pid=pid,cycle=cycle,current=current,
                    events=output,active=active,fresh=fresh,source='CANONICAL_OBSERVER_EVENTS')
    except (KeyError,TypeError,ValueError,AttributeError):
        return dict(schema_version=1,pid=None,cycle=None,current=None,
                    events=[],fresh=False,source='CANONICAL_OBSERVER_EVENTS')

class ActivityTrace:
    def __init__(self,root):
        self.root=Path(root)
        self.cycle=0
        self.events=[]
        self.active={}
        self.seq=0
        self._lock=threading.RLock()

    def emit(self,phase,state,**values):
        with self._lock:
            return self._emit(phase,state,**values)

    def _emit(self,phase,state,**values):
        if phase not in PHASES or state not in STATES:
            raise ValueError('invalid_activity_event')
        self.seq+=1
        event=dict(seq=self.seq,at_utc=datetime.now(timezone.utc).isoformat(),
                   phase=phase,state=state)
        for key in FIELDS+('count',):
            if key in values:
                event[key]=values[key]
        if phase in ('STOPPED','BLOCKED'): self.active.clear()
        elif phase in ('WAITING','DEGRADED'):
            self.active={p:e for p,e in self.active.items() if p in RESEARCH_PHASES}
        if state=='STARTED':self.active[phase]=event
        else:self.active.pop(phase,None)
        self.events=(self.events+[event])[-80:]
        data=clean_activity(dict(pid=os.getpid(),cycle=self.cycle,events=self.events,active=list(self.active.values())))
        try:
            journal=self.root/'activity-history.jsonl'
            if journal.exists() and journal.stat().st_size > 5*1024*1024:
                for index in (2,1):
                    older=self.root/('activity-history.'+str(index)+'.jsonl')
                    if older.exists(): older.replace(self.root/('activity-history.'+str(index+1)+'.jsonl'))
                journal.replace(self.root/'activity-history.1.jsonl')
            with journal.open('a',encoding='utf-8') as history:
                history.write(json.dumps(dict(pid=os.getpid(),cycle=self.cycle,**event),allow_nan=False)+'\n')
            temp=self.root/'runtime-activity.tmp'
            temp.write_text(json.dumps(data,allow_nan=False)+'\n',encoding='utf-8')
            replace_snapshot(temp,self.root/'runtime-activity.json')
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
