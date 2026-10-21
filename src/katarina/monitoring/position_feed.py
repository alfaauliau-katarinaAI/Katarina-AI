"""Explicit position/PnL projection; all other account and outbox data stay private."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite,fsum
from pathlib import Path
import re
import sqlite3
from katarina.monitoring.worker_runtime import _read,_fresh,read_independent_demo_monitor
from katarina.monitoring.entry_feed import _db,_price,_symbol


def amount(value):
    return value if type(value) in (int,float) and isfinite(value) and abs(value)<1e12 else None


def read_position_feed(root,*,allowed,now=None):
    now=now or datetime.now(timezone.utc);root=Path(root)
    empty=dict(status='NOT_ATTESTED',positions=[])
    latest=_read(root/'latest.json');monitor=latest.get('broker_account_monitor') or {}
    observer_fresh=_fresh(latest,now,90,'observed_at_utc')
    independent=read_independent_demo_monitor(root,now=now) if allowed else {}
    if independent:
        monitor=independent
    snapshot=monitor.get('position_snapshot') or {}
    if not (allowed and (observer_fresh or bool(independent)) and monitor.get('connected') is True
            and monitor.get('positions_read_success') is True and snapshot.get('status')=='OBSERVED'
            and snapshot.get('as_of_utc')==monitor.get('observed_at_utc',snapshot.get('as_of_utc')) and _fresh(snapshot,now)
            and isinstance(snapshot.get('currency'),str) and re.fullmatch(r'[A-Z][A-Z0-9]{2,7}',snapshot['currency'])):
        return empty
    owned={};ownership=False
    # OPEN is broker-reconciled ownership. ACCEPTED/UNKNOWN are never inferred as fills.
    try:
        with closing(_db(root/'demo-forward/orders.sqlite3')) as db:
            rows=db.execute("SELECT position_id,intent_json FROM demo_outbox WHERE state='OPEN' LIMIT 100").fetchall()
        for ident,raw in rows:
            intent=json.loads(raw)
            if type(ident) is int and ident>0:
                owned[sha256(('position:'+str(ident)).encode()).hexdigest()[:24]]=(intent.get('symbol'),intent.get('side'))
        ownership=snapshot.get('mode')=='DEMO'
    except (OSError,ValueError,TypeError,sqlite3.Error):
        pass
    positions=[]
    for p in snapshot.get('positions',[])[:100]:
        if not isinstance(p,dict) or not re.fullmatch('[a-f0-9]{24}',str(p.get('id',''))) or not _symbol(p.get('symbol')) or p.get('side') not in ('BUY','SELL'):
            continue
        try:
            stamp=datetime.fromisoformat(p['opened_utc']) if p.get('opened_utc') else None
            if stamp is not None and (stamp.tzinfo is None or stamp>now):continue
        except (ValueError,TypeError,KeyError):continue
        row=dict(id=p['id'],symbol=p['symbol'],side=p['side'],opened_utc=p['opened_utc'],
                 owner='KATARINA_DEMO' if ownership and owned.get(p['id'])==(p['symbol'],p['side']) else 'UNATTRIBUTED')
        for key in ('entry_price','current_price'):row[key]=_price(p.get(key))
        for key in ('stop_loss','take_profit'):
            v=p.get(key);row[key]=v if type(v) in (int,float) and isfinite(v) and 0<=v<1e12 else None
        row['profit']=amount(p.get('profit'));row['swap']=amount(p.get('swap'))
        row['floating']=row['profit']+row['swap'] if row['profit'] is not None and row['swap'] is not None else None
        positions.append(row)
    total=snapshot.get('total_count');count=total if type(total) is int and 0<=total<=10000 else None
    own=[p for p in positions if p['owner']=='KATARINA_DEMO']
    complete=count==len(positions)
    return dict(status='OBSERVED',as_of_utc=snapshot['as_of_utc'],currency=snapshot['currency'],mode=snapshot.get('mode'),
        positions=positions,total_count=count,truncated=not complete,floating_total=amount(snapshot.get('floating_total')),
        katarina_floating=fsum(p['floating'] for p in own) if ownership and complete and all(p['floating'] is not None for p in own) else None,
        pnl_basis='PROFIT_PLUS_SWAP_EXCLUDES_OPEN_COMMISSION')
