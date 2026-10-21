"""Bounded monthly CLOSED-bar history, independent of a terminal position cap."""
from datetime import datetime, timezone, timedelta
import numpy as np


def load_calendar_history(fetch, symbol, timeframe, seconds, start, end, *, now=None):
    now = now or datetime.now(timezone.utc)
    if any(t.tzinfo is None for t in (start,end,now)) or not 0 < (end-start).total_seconds() <= 730*86400:
        raise ValueError('invalid_historical_calendar_range')
    cutoff=min(end,now)
    if start>=cutoff or seconds not in (300,900,3600):
        raise ValueError('invalid_historical_cutoff_or_timeframe')
    cursor=start
    chunks,months=[],[]
    while cursor<cutoff:
        boundary=(datetime(cursor.year+1,1,1,tzinfo=timezone.utc) if cursor.month==12
                  else datetime(cursor.year,cursor.month+1,1,tzinfo=timezone.utc))
        stop=min(boundary,cutoff)
        rows=fetch(symbol,timeframe,cursor,stop-timedelta(microseconds=1))
        count=0
        if rows is not None and len(rows):
            rows=np.asarray(rows)
            valid=((rows['time']>=cursor.timestamp()) & (rows['time']<stop.timestamp())
                   & (rows['time']+seconds<=cutoff.timestamp())
                   & (rows['open']>0) & (rows['close']>0)
                   & (rows['high']>=np.maximum(rows['open'],rows['close']))
                   & (rows['low']<=np.minimum(rows['open'],rows['close']))
                   & (rows['spread']>=0))
            for field in ('open','high','low','close'):
                valid &= np.isfinite(rows[field])
            rows=rows[valid]
            count=len(rows)
            if count:chunks.append(rows)
        months.append(dict(month=cursor.strftime('%Y-%m'),returned_closed_bars=count))
        cursor=stop
    if not chunks:
        return None,dict(months=months,missing_months=[m['month'] for m in months])
    data=np.sort(np.concatenate(chunks),order='time')
    _,indices=np.unique(data['time'],return_index=True)
    if len(indices)!=len(data):
        raise ValueError('duplicate_monthly_history_timestamp')
    return data,dict(months=months,missing_months=[m['month'] for m in months if m['returned_closed_bars']==0],
        first_timestamp=int(data['time'][0]),last_timestamp=int(data['time'][-1]),
        bars=len(data),full_session_completeness_verified=False)
