"""Persistent, bounded repair of broker sensor gaps inside the canonical owner thread."""
from katarina.monitoring.snapshot_io import replace_snapshot
from datetime import datetime,timezone,timedelta
import json,os,math
from hashlib import sha256
from pathlib import Path
from katarina.intelligence.broker.causal_broker_quotes import last_past_quote,market_event_clock,closed_bars_as_of_market_tick
from katarina.adapters.mt5_readonly_market import bars_for,TF

REASONS=frozenset(('symbol_select_denied','invalid_symbol_or_quote','no_past_broker_bidask_quote',
 'stale_market_tick','broker_tick_from_future','insufficient_past_only_closed_bars',
 'insufficient_completed_bars_as_of_mt5_tick','insufficient_closed_M5','insufficient_closed_M15',
 'insufficient_closed_H1','INPUTS_READY_AWAIT_OBSERVATION','SENSOR_READ_FAILED',
 'SYMBOL_DISABLED','SYMBOL_CLOSE_ONLY','HISTORY_AVAILABLE_LIVE_QUOTE_MISSING','STALE_CLOSED_BARS',
 'CORE_SYMBOL_UNAVAILABLE'))
def reason_code(error):
    return str(error) if str(error) in REASONS else 'SENSOR_READ_FAILED'

def setup(db):
    db.execute('''CREATE TABLE IF NOT EXISTS sensor_recovery(symbol TEXT PRIMARY KEY,
      reason TEXT NOT NULL,status TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
      next_epoch REAL NOT NULL DEFAULT 0,updated_utc TEXT NOT NULL,methods TEXT NOT NULL DEFAULT '[]')''')

def record_gaps(db,cards,quotes,now,root):
    setup(db)
    with db:
        for symbol,card in cards.items():
            quality=card.get('sensor_quality') or {}
            quality_reason=('SYMBOL_DISABLED' if quality.get('trade_mode')==0 else
                            'SYMBOL_CLOSE_ONLY' if quality.get('trade_mode')==3 else
                            'STALE_CLOSED_BARS' if quality.get('closed_bars_recent') is False else None)
            if symbol in quotes and quality_reason is None:
                db.execute("UPDATE sensor_recovery SET status='VERIFIED',updated_utc=? WHERE symbol=?",(now.isoformat(),symbol))
            else:
                code=quality_reason or card.get('sensor_reason','SENSOR_READ_FAILED')
                code=code if code in REASONS else 'SENSOR_READ_FAILED'
                db.execute('''INSERT INTO sensor_recovery(symbol,reason,status,updated_utc) VALUES(?,?,'PENDING',?)
                  ON CONFLICT(symbol) DO UPDATE SET reason=excluded.reason,
                  status=CASE WHEN sensor_recovery.status='VERIFIED' THEN 'PENDING' ELSE sensor_recovery.status END,
                  updated_utc=excluded.updated_utc''',(symbol,code,now.isoformat()))
    return save_summary(db,root,now)

def save_summary(db,root,now):
    setup(db)
    counts=dict(db.execute('SELECT status,COUNT(*) FROM sensor_recovery GROUP BY status'))
    reasons=dict(db.execute("SELECT reason,COUNT(*) FROM sensor_recovery WHERE status!='VERIFIED' GROUP BY reason"))
    out=dict(schema_version=1,pid=os.getpid(),as_of_utc=now.isoformat(),status='ACTIVE_RECOVERY',
       missing=sum(v for k,v in counts.items() if k!='VERIFIED'),verified=counts.get('VERIFIED',0),
       attempts=db.execute('SELECT COALESCE(SUM(attempts),0) FROM sensor_recovery').fetchone()[0],
       inputs_ready=counts.get('INPUTS_READY_RECHECK',0),reasons=reasons,live_authorized=False,
       methods=['SYMBOL_SUBSCRIPTION','RECENT_TICK_WINDOW','SEGMENTED_TICK_WINDOWS','MULTITIMEFRAME_BAR_WARMUP'])
    path=Path(root)/'data-recovery.json';temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(out)+'\n',encoding='utf-8');replace_snapshot(temp,path)
    return out

def date_range_warmup(broker,symbol,now,attempts):
    method=getattr(broker,'copy_rates_range',None)
    if not callable(method) or attempts<1:return {}
    stage=attempts%3+1;summary={}
    for (label,(name,_)),days in zip(TF.items(),(2*stage,7*stage,30*stage)):
        rows=method(symbol,getattr(broker,name),now-timedelta(days=days),now)
        if rows is None or len(rows)>4096:
            summary[label]={'status':'UNAVAILABLE_OR_OVERSIZE'};continue
        valid=[]
        for row in rows:
            stamp=int(row['time']);values=[float(row[k]) for k in ('open','high','low','close')]
            if stamp<=0 or not all(math.isfinite(v) and v>0 for v in values) or not values[2]<=min(values[0],values[3])<=max(values[0],values[3])<=values[1]:continue
            valid.append([stamp,*values])
        summary[label]={'rows':len(valid),'days_requested':days,
                        'digest':sha256(json.dumps(valid,separators=(',',':')).encode()).hexdigest(),
                        'validated_for_entry':False}
    return summary


def recover_due(db,broker,root,now,*,emit=lambda *a,**k:None,budget=2):
    """No parallel MT5 clients; at most two symbols, no execution or synthetic quotes."""
    if type(budget) is not int or not 1<=budget<=2:raise ValueError('invalid_recovery_budget')
    setup(db)
    db.execute('CREATE TABLE IF NOT EXISTS sensor_recovery_attempts(id INTEGER PRIMARY KEY,report_json TEXT NOT NULL)')
    db.commit()
    terminal=broker.terminal_info()
    from katarina.adapters.demo_permissions import observation_permission
    if not observation_permission(broker,terminal):raise RuntimeError('ACCOUNT_OR_TRADING_PERMISSION_CHANGED')
    jobs=db.execute("SELECT symbol,attempts FROM sensor_recovery WHERE status!='VERIFIED' AND next_epoch<=? ORDER BY next_epoch,attempts,symbol LIMIT ?",(now.timestamp(),budget)).fetchall()
    for symbol,attempts in jobs:
        emit('HISTORY','STARTED',symbol=symbol,action='DATA_RECOVERY')
        methods=[];status='RETRY_SCHEDULED';reason='SENSOR_READ_FAILED';history={}
        try:
            methods.append('SYMBOL_SUBSCRIPTION')
            if not broker.symbol_select(symbol,True):raise ValueError('symbol_select_denied')
            broker.symbol_info_tick(symbol)
            info=broker.symbol_info(symbol) if callable(getattr(broker,'symbol_info',None)) else None
            mode=getattr(info,'trade_mode',None)
            if mode==0:raise ValueError('SYMBOL_DISABLED')
            if mode==3:raise ValueError('SYMBOL_CLOSE_ONLY')
            history=date_range_warmup(broker,symbol,now,attempts)
            if history:methods.append('DATE_RANGE_HISTORY_WARMUP')
            # Request larger bounded history buffers before normal candle validation.
            methods.append('MULTITIMEFRAME_BAR_WARMUP')
            for name,_ in TF.values():broker.copy_rates_from_pos(symbol,getattr(broker,name),1,512)
            with (Path(root)/'latest.json').open('rb') as f:raw=f.read(2_000_001)
            if len(raw)>2_000_000:raise ValueError('snapshot_too_large')
            shift=json.loads(raw).get('broker_server_shift_hours')
            if type(shift) is not int or not -12<=shift<=14:raise ValueError('clock_not_verified')
            methods.append('RECENT_TICK_WINDOW');quote=last_past_quote(
                broker,symbol,now,server_shift_hours=shift)
            if quote is None:
                raise ValueError('HISTORY_AVAILABLE_LIVE_QUOTE_MISSING' if any(v.get('rows',0)>0 for v in history.values()) else 'no_past_broker_bidask_quote')
            market=market_event_clock(quote[2],now).market_utc
            bars=bars_for(broker,symbol,timedelta(hours=shift))
            for label,rows in bars.items():
                valid=closed_bars_as_of_market_tick(rows,market)
                if not 0<=(market-valid[-1].closed_at_utc).total_seconds()<=TF[label][1]*120:
                    raise ValueError('STALE_CLOSED_BARS')
            status='INPUTS_READY_RECHECK';reason='INPUTS_READY_AWAIT_OBSERVATION'
            emit('HISTORY','DONE',symbol=symbol,action='RECOVERY_INPUTS_READY')
        except Exception as ex:
            from katarina.adapters.automatic_connection import ConnectionUnavailable
            if isinstance(ex,ConnectionUnavailable):raise
            reason=reason_code(ex)
            if reason in ('SYMBOL_DISABLED','SYMBOL_CLOSE_ONLY'):status='WAIT_BROKER_PERMISSION'
            elif reason=='HISTORY_AVAILABLE_LIVE_QUOTE_MISSING':status='HISTORY_RESEARCH_ONLY'
            emit('HISTORY','FAILED',symbol=symbol,action=reason)
        with db:
            db.execute('INSERT INTO sensor_recovery_attempts(report_json) VALUES(?)',(json.dumps({'symbol':symbol,'observed_utc':now.isoformat(),'status':status,'reason':reason,'methods':methods,'history':history,'session_status':'NOT_INFERRED_FROM_MISSING_QUOTES','live_authorized':False},allow_nan=False),))
            # Missing/closed markets cannot be manufactured; retry with bounded backoff.
            delay=min(900,30*2**min(attempts,5))
            db.execute('UPDATE sensor_recovery SET reason=?,status=?,attempts=attempts+1,next_epoch=?,updated_utc=?,methods=? WHERE symbol=?',
                       (reason,status,now.timestamp()+delay,now.isoformat(),json.dumps(methods),symbol))
    return save_summary(db,root,now)

def read_recovery(root,pid):
    try:
        raw=(Path(root)/'data-recovery.json').read_bytes()
        if len(raw)>8192:return {'status':'NOT_ATTESTED'}
        v=json.loads(raw)
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(v['as_of_utc'])).total_seconds()
        if v.get('pid')!=pid or not -30<=age<=180 or v.get('live_authorized') is not False:return {'status':'NOT_ATTESTED'}
        out={'status':'ACTIVE_RECOVERY','as_of_utc':v['as_of_utc'],'live_authorized':False}
        for k in ('missing','verified','attempts','inputs_ready'):
            n=v.get(k);out[k]=n if type(n) is int and 0<=n<=100000000 else None
        out['reasons']={k:n for k,n in v.get('reasons',{}).items() if k in REASONS and type(n) is int and 0<=n<=1000}
        return out
    except (OSError,ValueError,TypeError,KeyError,AttributeError):return {'status':'NOT_ATTESTED'}

def seed_existing_gaps(db,root,now):
    """Old diagnostics seed read requests only; they are never fresh-market evidence."""
    try:
        raw=(Path(root)/'latest.json').read_bytes()
        if len(raw)>2_000_000:raise ValueError('snapshot_too_large')
        cards=json.loads(raw).get('symbols',{})
        failed={symbol:card for symbol,card in cards.items() if isinstance(card,dict)
                and (card.get('sensor_reason') or card.get('sensor_quality',{}).get('closed_bars_recent') is False or card.get('sensor_quality',{}).get('trade_mode') in (0,3) or any(str(x).startswith('sensor_error:') for x in card.get('blocking_reasons',[])))}
        return record_gaps(db,failed,{},now,root)
    except (OSError,ValueError,TypeError,AttributeError):return save_summary(db,root,now)
