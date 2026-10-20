"""Evidence-scoped broker time calibration; owner-thread reads, never orders."""
from katarina.monitoring.snapshot_io import replace_snapshot
from contextlib import closing
from datetime import datetime,timezone
from hashlib import sha256
import json,math,os,shutil,sqlite3,time,zlib
from pathlib import Path


def compare_window(bar,ticks,offset_minutes,now_epoch,point):
    start=int(bar['time'])-offset_minutes*60;end=start+300
    out={'offset_minutes':offset_minutes,'raw_open':int(bar['time']),'utc_open':start,'matched':False}
    if end>now_epoch:return dict(out,reason='WINDOW_NOT_CLOSED')
    if ticks is None or not 5<=len(ticks)<=25000:return dict(out,reason='TICK_COVERAGE_UNAVAILABLE')
    values=[];previous=None
    for row in ticks:
        t=float(row['time_msc'])/1000;bid=float(row['bid']);ask=float(row['ask'])
        if not all(math.isfinite(v) for v in (t,bid,ask)) or not start<=t<end or bid<=0 or ask<bid or (previous is not None and t<previous):
            return dict(out,reason='INVALID_OR_NONCAUSAL_TICKS')
        values.append([int(row['time_msc']),bid,ask]);previous=t
    prices=[v[1] for v in values];actual=[prices[0],max(prices),min(prices),prices[-1]]
    expected=[float(bar[k]) for k in ('open','high','low','close')]
    if not math.isfinite(point) or point<=0 or not all(math.isfinite(v) and v>0 for v in expected):
        return dict(out,reason='INVALID_PRICE_GRID')
    coverage=int(bar['tick_volume'])==len(values)
    ohlc_matches=all(abs(a-b)<=point*.51 for a,b in zip(actual,expected))
    matched=coverage and ohlc_matches
    return dict(out,reason='TICK_VOLUME_COVERAGE_MISMATCH' if not coverage else 'OHLC_AND_VOLUME_MATCH' if matched else 'OHLC_MISMATCH',matched=matched,ohlc_matches=ohlc_matches,tick_coverage_complete=coverage,expected_tick_volume=int(bar['tick_volume']),
                ticks=len(values),tick_digest=sha256(json.dumps(values,separators=(',',':')).encode()).hexdigest(),
                expected_ohlc=expected,actual_ohlc=actual)


def _db(root):
    db=sqlite3.connect(Path(root)/'calibration.sqlite3',timeout=2)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS calibration_meta(key TEXT PRIMARY KEY,value REAL)')
    db.execute('CREATE TABLE IF NOT EXISTS calibration_targets(symbol TEXT PRIMARY KEY,last_checked REAL NOT NULL DEFAULT 0,visits INTEGER NOT NULL DEFAULT 0,history_cursor INTEGER NOT NULL DEFAULT 0)')
    db.execute('CREATE TABLE IF NOT EXISTS calibration_pending(id TEXT PRIMARY KEY,symbol TEXT,bars_json TEXT,historical INTEGER,attempts INTEGER,next_epoch REAL,status TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS calibration_runs(id TEXT PRIMARY KEY,symbol TEXT,observed_utc TEXT,report_json TEXT,ticks_zlib BLOB)')
    db.execute('CREATE TABLE IF NOT EXISTS calibration_conflicts(symbol TEXT,raw_open INTEGER,run_id TEXT,PRIMARY KEY(symbol,raw_open,run_id))')
    db.execute('CREATE TABLE IF NOT EXISTS calibrated_windows(symbol TEXT,raw_open INTEGER,offset_minutes INTEGER,run_id TEXT,PRIMARY KEY(symbol,raw_open))')
    db.commit();return db


def verified_window_offset(db,symbol,raw_open):
    row=db.execute('SELECT w.offset_minutes FROM calibrated_windows w WHERE w.symbol=? AND w.raw_open=? AND NOT EXISTS(SELECT 1 FROM calibration_conflicts c WHERE c.symbol=w.symbol AND c.raw_open=w.raw_open)',(symbol,raw_open)).fetchone()
    return row[0] if row else None


def calibrate_due(context,broker,root,now,*,emit=lambda *a,**k:None):
    if now.tzinfo is None:raise ValueError('EXPLICIT_UTC_REQUIRED')
    root=Path(root);stamp=now.timestamp()
    if (root/'continuous.stop').exists():return {'status':'OWNER_STOP_REQUEST'}
    from katarina.adapters.demo_permissions import observation_permission
    if not observation_permission(broker):raise RuntimeError('ACCOUNT_OR_TRADING_PERMISSION_CHANGED')
    with closing(_db(root)) as db:
        old=db.execute("SELECT value FROM calibration_meta WHERE key='last_attempt'").fetchone()
        if old and stamp-old[0]<60:return {'status':'WAIT_CALIBRATION_INTERVAL'}
        size=sum(p.stat().st_size for p in (root/'calibration.sqlite3',root/'calibration.sqlite3-wal') if p.exists())
        if shutil.disk_usage(root).free<2*1024**3 or size>128*1024**2:
            return {'status':'CALIBRATION_STORAGE_REVIEW_REQUIRED'}
        names=[r[0] for r in context.execute('SELECT symbol FROM lab_universe ORDER BY symbol')]
        if not names:return {'status':'NO_CALIBRATION_TARGETS'}
        with db:
            db.executemany('INSERT OR IGNORE INTO calibration_targets(symbol) VALUES(?)',[(s,) for s in names])
            pending=db.execute("SELECT id,symbol,bars_json,historical,attempts FROM calibration_pending WHERE status='PENDING' AND next_epoch<=? ORDER BY next_epoch,id LIMIT 1",(stamp,)).fetchone()
            attempt_index=db.execute('SELECT COALESCE(SUM(visits),0) FROM calibration_targets').fetchone()[0]
            symbol,visits,cursor=db.execute("SELECT symbol,visits,history_cursor FROM calibration_targets ORDER BY last_checked,CASE WHEN symbol LIKE 'EURUSD%' THEN 0 WHEN symbol LIKE 'GBPUSD%' THEN 1 ELSE 2 END,symbol LIMIT 1").fetchone()
            if pending:
                symbol=pending[1]
                visits,cursor=db.execute('SELECT visits,history_cursor FROM calibration_targets WHERE symbol=?',(symbol,)).fetchone()
            db.execute("INSERT OR REPLACE INTO calibration_meta VALUES('last_attempt',?)",(stamp,))
            db.execute('UPDATE calibration_targets SET last_checked=?,visits=visits+1 WHERE symbol=?',(stamp,symbol))
        emit('VALIDATE','STARTED',symbol=symbol,action='AUTONOMOUS_CLOCK_CALIBRATION')
        report={'symbol':symbol,'scope':'TWO_M5_WINDOWS_ONLY','historical_dst_verified':False,'live_authorized':False,'status':'UNRESOLVED'}
        payload=b'';bars=None;historical=False
        started_id=sha256((symbol+'|'+now.isoformat()+'|STARTED').encode()).hexdigest()
        with db:db.execute('INSERT OR IGNORE INTO calibration_runs VALUES(?,?,?,?,?)',(started_id,symbol,now.isoformat(),json.dumps(dict(report,status='STARTED')),b''))
        try:
            raw=(root/'latest.json').read_bytes()
            if len(raw)>2_000_000:raise ValueError('CLOCK_SNAPSHOT_TOO_LARGE')
            reference=json.loads(raw)['time_reference'];observed=datetime.fromisoformat(reference['observed_at_utc'])
            base=reference.get('broker_server_shift_minutes')
            if observed.tzinfo is None or not 0<=stamp-observed.timestamp()<=180 or type(base) is not int or reference.get('confirming_symbols',0)<3 or reference.get('canonical_market_clock')!='MT5_COPY_TICKS_RANGE_TIME_MSC_UTC':
                raise ValueError('CURRENT_CLOCK_REFERENCE_UNVERIFIED')
            info=broker.symbol_info(symbol)
            if info is None or getattr(info,'chart_mode',None)!=0:raise ValueError('BID_CHART_SOURCE_NOT_VERIFIED')
            broker.symbol_select(symbol,True)
            historical=bool(pending[3]) if pending else visits%2==1 or (visits==0 and attempt_index%2==1)
            if pending:rates=json.loads(pending[2])
            elif historical:
                boundary=cursor or int(stamp+base*60)-270*86400
                row=context.execute('SELECT stamp FROM lab_bars WHERE symbol=? AND stamp<? ORDER BY stamp DESC LIMIT 1',(symbol,boundary)).fetchone()
                if not row and not cursor:
                    row=context.execute('SELECT stamp FROM lab_bars WHERE symbol=? AND stamp<? ORDER BY stamp LIMIT 1',(symbol,int(stamp+base*60)-86400)).fetchone()
                if not row:
                    with db:db.execute('UPDATE calibration_targets SET history_cursor=0 WHERE symbol=?',(symbol,))
                    raise ValueError('HISTORICAL_ANCHOR_NOT_AVAILABLE')
                anchor=int(row[0]);start=datetime.fromtimestamp(anchor,timezone.utc);end=datetime.fromtimestamp(anchor+3600,timezone.utc)
                rates=broker.copy_rates_range(symbol,broker.TIMEFRAME_M5,start,end)
                with db:db.execute('UPDATE calibration_targets SET history_cursor=? WHERE symbol=?',((anchor//86400)*86400,symbol))
            else:rates=broker.copy_rates_from_pos(symbol,broker.TIMEFRAME_M5,1,8)
            if rates is None or not 2<=len(rates)<=32:raise ValueError('CALIBRATION_BARS_UNAVAILABLE')
            bars=sorted(rates,key=lambda r:int(r['time']))[-2:]
            bars=[{'time':int(b['time']),'tick_volume':int(b['tick_volume']),**{k:float(b[k]) for k in ('open','high','low','close')}} for b in bars]
            if any(int(b['time'])<=0 or int(b['time'])%300 for b in bars) or int(bars[1]['time'])-int(bars[0]['time'])<300:raise ValueError('CALIBRATION_WINDOWS_OVERLAP')
            offsets=sorted({0,base-60,base,base+60});offsets=[v for v in offsets if -720<=v<=840]
            results=[];matches=[];proofs={}
            for offset in offsets:
                evidence=[];frozen=[]
                for bar in bars:
                    if (root/'continuous.stop').exists():raise ValueError('OWNER_STOP_REQUEST')
                    start=int(bar['time'])-offset*60;end=start+300
                    ticks=None
                    if end<=stamp:
                        ticks=broker.copy_ticks_range(symbol,datetime.fromtimestamp(start,timezone.utc),datetime.fromtimestamp(end,timezone.utc),broker.COPY_TICKS_INFO)
                        # The API's right boundary may be inclusive; only the
                        # exact half-open candle interval belongs to this proof.
                        if ticks is not None and len(ticks)<=25000:ticks=[r for r in ticks if start*1000<=int(r['time_msc'])<end*1000]
                    finding=compare_window(bar,ticks,offset,stamp,float(info.point))
                    finding['tick_source']='COPY_TICKS_INFO'
                    all_ticks=getattr(broker,'COPY_TICKS_ALL',None)
                    if finding['reason']=='TICK_VOLUME_COVERAGE_MISMATCH' and type(all_ticks) is int:
                        ticks=broker.copy_ticks_range(symbol,datetime.fromtimestamp(start,timezone.utc),datetime.fromtimestamp(end,timezone.utc),all_ticks)
                        if ticks is not None and len(ticks)<=25000:ticks=[r for r in ticks if start*1000<=int(r['time_msc'])<end*1000]
                        finding=compare_window(bar,ticks,offset,stamp,float(info.point))
                        finding.update(tick_source='COPY_TICKS_ALL',initial_stream_reason='TICK_VOLUME_COVERAGE_MISMATCH')
                    evidence.append(finding)
                    if finding['matched']:frozen.append([[int(t['time_msc']),float(t['bid']),float(t['ask'])] for t in ticks])
                results.append({'offset_minutes':offset,'windows':evidence})
                if all(v['matched'] for v in evidence):matches.append(offset);proofs[offset]=frozen
            report.update(historical=historical,tested_offsets=offsets,results=results,matching_offsets=matches,
                          alignment_candidates=[x['offset_minutes'] for x in results if all(w.get('ohlc_matches') for w in x['windows'])])
            if len(matches)==1:
                report.update(status='MATCHED_WINDOW_ALIGNMENT',offset_minutes=matches[0],raw_windows=[int(b['time']) for b in bars])
                payload=zlib.compress(json.dumps(proofs[matches[0]],separators=(',',':')).encode())
            elif len(matches)>1:report['status']='AMBIGUOUS_WINDOW_ALIGNMENT'
            else:report['status']='MORE_BROKER_EVIDENCE_REQUIRED'
        except Exception as exc:
            from katarina.adapters.automatic_connection import ConnectionUnavailable
            if isinstance(exc,ConnectionUnavailable):raise
            report['status']='MORE_BROKER_EVIDENCE_REQUIRED'
            report['reason']=str(exc) if type(exc) is ValueError and str(exc) in {'CLOCK_SNAPSHOT_TOO_LARGE','CURRENT_CLOCK_REFERENCE_UNVERIFIED','BID_CHART_SOURCE_NOT_VERIFIED','HISTORICAL_ANCHOR_NOT_AVAILABLE','CALIBRATION_BARS_UNAVAILABLE','CALIBRATION_WINDOWS_OVERLAP','OWNER_STOP_REQUEST'} else type(exc).__name__
        ident=sha256((symbol+'|'+now.isoformat()+'|'+json.dumps(report,sort_keys=True)).encode()).hexdigest()
        with db:
            conflicts=[]
            if report['status']=='MATCHED_WINDOW_ALIGNMENT':
                for raw_open in report['raw_windows']:
                    previous=db.execute('SELECT offset_minutes FROM calibrated_windows WHERE symbol=? AND raw_open=?',(symbol,raw_open)).fetchone()
                    if previous is not None and previous[0]!=report['offset_minutes']:conflicts.append(raw_open)
                if conflicts:
                    report['status']='CONFLICTING_WINDOW_EVIDENCE'
                    for raw_open in conflicts:db.execute('INSERT OR IGNORE INTO calibration_conflicts VALUES(?,?,?)',(symbol,raw_open,ident))
                else:
                    for raw_open in report['raw_windows']:db.execute('INSERT OR IGNORE INTO calibrated_windows VALUES(?,?,?,?)',(symbol,raw_open,report['offset_minutes'],ident))
            db.execute('INSERT OR IGNORE INTO calibration_runs VALUES(?,?,?,?,?)',(ident,symbol,now.isoformat(),json.dumps(report,allow_nan=False),payload))
            if pending:
                state='DONE' if report['status']=='MATCHED_WINDOW_ALIGNMENT' else 'REVIEW' if report['status'] in ('AMBIGUOUS_WINDOW_ALIGNMENT','CONFLICTING_WINDOW_EVIDENCE') else 'PENDING'
                count=pending[4]+1
                db.execute('UPDATE calibration_pending SET attempts=?,next_epoch=?,status=? WHERE id=?',(count,stamp+(120 if count<3 else 21600),state,pending[0]))
            elif bars is not None and report['status']=='MORE_BROKER_EVIDENCE_REQUIRED':
                key=sha256((symbol+'|'+str([b['time'] for b in bars])).encode()).hexdigest()
                db.execute("INSERT OR IGNORE INTO calibration_pending VALUES(?,?,?,?,?,?,?)",(key,symbol,json.dumps(bars),int(historical),1,stamp+120,'PENDING'))

        summary={'pid':os.getpid(),'as_of_utc':now.isoformat(),'status':report['status'],'symbol':symbol,
                 'runs':db.execute("SELECT COUNT(*) FROM calibration_runs WHERE json_extract(report_json,'$.status')!='STARTED'").fetchone()[0],
                 'verified_windows':db.execute('SELECT COUNT(*) FROM calibrated_windows w WHERE NOT EXISTS(SELECT 1 FROM calibration_conflicts c WHERE c.symbol=w.symbol AND c.raw_open=w.raw_open)').fetchone()[0],
                 'pending_windows':db.execute("SELECT COUNT(*) FROM calibration_pending WHERE status='PENDING'").fetchone()[0],
                 'historical_dst_verified':False,'live_authorized':False}
        tmp=root/'calibration.tmp';tmp.write_text(json.dumps(summary)+'\n',encoding='utf-8');replace_snapshot(tmp,root/'calibration.json')
        emit('VALIDATE','DONE' if report['status']=='MATCHED_WINDOW_ALIGNMENT' else 'IDLE',symbol=symbol,action='CALIBRATION_EVIDENCE_SAVED')
        return summary
