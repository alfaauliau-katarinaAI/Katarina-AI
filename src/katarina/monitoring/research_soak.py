"""Persist self-reported soak evidence across restarts; never grants execution."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from contextlib import closing


def record_soak(root, status):
    root=Path(root)
    stamp=datetime.fromisoformat(status['heartbeat_utc']).timestamp()
    safe=(status.get('orders_submitted')==0 and status.get('live_execution_authorized') is False
          and status.get('production_execution') is False and status.get('delivery','DISABLED')=='DISABLED')
    with closing(sqlite3.connect(root/'research-soak.sqlite3')) as db:
        db.execute('CREATE TABLE IF NOT EXISTS samples(stamp REAL PRIMARY KEY, run_id TEXT, phase TEXT, safe INTEGER)')
        db.execute('INSERT OR IGNORE INTO samples VALUES(?,?,?,?)',(stamp,status['run_id'],status['status'],int(safe)))
        # Keep eight days of operational samples; original research evidence is untouched.
        db.execute('DELETE FROM samples WHERE stamp<?',(stamp-8*86400,))
        db.commit()
        rows=db.execute('SELECT stamp,phase,safe FROM samples ORDER BY stamp').fetchall()
        start=rows[0][0];elapsed=stamp-start
        windows={}
        for name,seconds in (('24_hours',86400),('7_days',604800)):
            points=[r for r in rows if r[0]>=stamp-seconds]
            max_gap=max([b[0]-a[0] for a,b in zip(points,points[1:])]+[max(0,points[0][0]-max(start,stamp-seconds)),stamp-points[-1][0]])
            faults=sum(r[1] in ('BLOCKED','DEGRADED','STOPPED') or not r[2] for r in points)
            windows[name]=dict(status='PENDING_ELAPSED_TIME' if elapsed<seconds else
                              'SELF_REPORTED_PASS' if faults==0 and max_gap<=180 else 'NEEDS_REVIEW',
                              samples=len(points),fault_samples=faults,max_gap_seconds=round(max_gap,2))
        out=dict(schema_version=1,source='CANONICAL_PROCESS_SELF_REPORTED_NOT_INDEPENDENT_HOST_PROOF',
                 started_utc=datetime.fromtimestamp(start,timezone.utc).isoformat(),
                 updated_utc=status['heartbeat_utc'],elapsed_seconds=round(elapsed,2),
                 windows=windows,live_authorized=False)
    temp=root/'soak-status.tmp';temp.write_text(json.dumps(out)+'\n',encoding='utf-8');temp.replace(root/'soak-status.json')
    return out
