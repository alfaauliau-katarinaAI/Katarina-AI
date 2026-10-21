"""Incremental, resumable broker research. No execution or model promotion capability.

One history chunk and a bounded predeclared experiment per observation pass.
Historical diagnostics are never labelled independent holdout or broker fills.
"""
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil

VERSION = 'broker-lab-v2'
CHUNK = 2048
MAX_HISTORY = 65536
# Cost proxy: one live quote taken at rollover or on a stale market made the
# implied cost ~1 H1 range per trade (2026-10-19 memory: instrument explained
# 99% of results). Use the median of per-bar broker spreads instead.
MIN_SPREAD_SAMPLES = 100
# A typical spread above this share of the median H1 range leaves no room for
# any H1-horizon edge; such instruments are skipped, not tested and rejected.
MAX_SPREAD_TO_RANGE = 0.20
RANGE_WINDOW = 512


def catalog_symbols(catalog):
    import re
    return sorted({s.name for s in catalog if isinstance(getattr(s, 'name', None), str)
                   and re.fullmatch(r'[A-Za-z0-9_.#-]{1,40}', s.name)
                   and getattr(s, 'trade_mode', 0) in (1, 2, 4)})


def _field(row, key):
    try:
        return float(row[key])
    except (KeyError, IndexError, ValueError, TypeError):
        return None


def typical_spread(broker, symbol, block):
    """Median per-bar broker spread in price units; current quote only as fallback."""
    point = None
    try:
        info = broker.symbol_info(symbol)
        point = float(info.point) if info is not None else None
    except (AttributeError, TypeError, ValueError):
        point = None
    samples = []
    if point and math.isfinite(point) and point > 0 and block is not None:
        for row in block:
            value = _field(row, 'spread')
            if value is not None and math.isfinite(value) and value > 0:
                samples.append(value * point)
    tick = None
    try:
        quote = broker.symbol_info_tick(symbol)
        if quote and 0 < quote.bid <= quote.ask:
            tick = float(quote.ask - quote.bid)
    except (AttributeError, TypeError, ValueError):
        tick = None
    if len(samples) >= MIN_SPREAD_SAMPLES:
        samples.sort()
        middle = len(samples) // 2
        median = samples[middle] if len(samples) % 2 else (samples[middle - 1] + samples[middle]) / 2
        return dict(price=median, source='MEDIAN_H1_BAR_SPREAD', samples=len(samples), current_quote=tick)
    if tick is not None:
        return dict(price=tick, source='CURRENT_QUOTE_FALLBACK', samples=0, current_quote=tick)
    return None


def cost_gate(rows, spread):
    """Typical spread as a share of the median recent H1 range."""
    ranges = sorted(r[2] - r[3] for r in rows[-RANGE_WINDOW:] if r[2] - r[3] > 0)
    if not ranges:
        return None, True
    ratio = spread / ranges[len(ranges) // 2]
    return ratio, ratio > MAX_SPREAD_TO_RANGE


def setup(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS lab_universe(symbol TEXT PRIMARY KEY, seen_utc TEXT,
      scan_utc TEXT, status TEXT NOT NULL DEFAULT 'METADATA_ONLY', history_offset INTEGER NOT NULL DEFAULT 1,
      history_complete INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS lab_bars(symbol TEXT, stamp INTEGER, o REAL,h REAL,l REAL,c REAL,
      PRIMARY KEY(symbol,stamp));
    CREATE TABLE IF NOT EXISTS lab_runs(id TEXT PRIMARY KEY,symbol TEXT,created_utc TEXT,digest TEXT,result_json TEXT);
    CREATE TABLE IF NOT EXISTS lab_progress(id INTEGER PRIMARY KEY CHECK(id=1),cursor INTEGER NOT NULL);
    INSERT OR IGNORE INTO lab_progress VALUES(1,0);
    ''')


def select_batch(db, catalog, budget, now):
    setup(db)
    names = catalog_symbols(catalog)
    with db:
        db.executemany('INSERT INTO lab_universe(symbol,seen_utc) VALUES(?,?) ON CONFLICT(symbol) DO UPDATE SET seen_utc=excluded.seen_utc',
                       [(s, now.isoformat()) for s in names])
    # Oldest observed first, including symbols never visited. Stable tie breaker.
    visits = dict(db.execute('SELECT symbol,scan_utc FROM lab_universe'))
    picked = sorted(names, key=lambda s: (visits.get(s) or '', s))[:budget]
    with db:
        db.executemany('UPDATE lab_universe SET scan_utc=? WHERE symbol=?', [(now.isoformat(),s) for s in picked])
    return picked


def evaluate(rows, spread):
    """Frozen 3-pattern x BUY/SELL, nonoverlap 12-bar close exits; exploratory only."""
    outcomes = []
    for family in ('MOMENTUM', 'MEAN_REVERSION', 'BREAKOUT'):
        for side in (1,-1):
            values = [[], []]
            for i in range(32, len(rows)-13, 13):
                previous = rows[i-24:i]
                close = rows[i][4]
                atr = sum(r[2]-r[3] for r in rows[i-14:i])/14
                if atr <= 0: continue
                mean = sum(r[4] for r in previous)/24
                signal = ((close-previous[0][4])*side > atr if family=='MOMENTUM' else
                          (mean-close)*side > atr if family=='MEAN_REVERSION' else
                          close > max(r[2] for r in previous) if side==1 else close < min(r[3] for r in previous))
                if not signal: continue
                # Next open after completed signal, 12-bar close outcome; gaps remain uncertain.
                entry, exit_price = rows[i+1][1], rows[i+12][4]
                value = ((exit_price-entry)*side - max(spread, 0) - .2*atr)/atr
                cutoff=len(rows)*2//3
                if i+12 < cutoff: values[0].append(value)
                elif i >= cutoff: values[1].append(value)
            train, review = values
            outcomes.append(dict(method=family,side='BUY' if side==1 else 'SELL',
                development_n=len(train),development_mean_r=sum(train)/len(train) if train else None,
                review_n=len(review),review_mean_r=sum(review)/len(review) if review else None))
    qualified = [x for x in outcomes if x['development_n'] >= 30]
    candidate = max(qualified, key=lambda x:x['development_mean_r']) if qualified else None
    return dict(candidates=outcomes,selected=candidate,status='HYPOTHESIS_ONLY' if candidate else 'INSUFFICIENT_SAMPLES',
        execution_model='H1_NEXT_OPEN_12_BAR_CLOSE_NO_SL_TP',cost_model='CURRENT_SPREAD_PLUS_0.20_ATR_PROXY',
        independent_holdout=False,history_reused=True,broker_fill_verified=False,
        improvement_verified=False,live_authorized=False,
        limitations=['Historical exploration; no independent holdout','Current spread is not historical fill cost',
                    'Gaps, commission, swap, slippage and margin unresolved','No automatic promotion'])


def step(db, broker, root, now, *, emit=lambda *a,**k:None):
    setup(db)
    names = [r[0] for r in db.execute('SELECT symbol FROM lab_universe ORDER BY symbol')]
    if not names: return save_summary(root, summary(db, now, 'EMPTY_UNIVERSE'))
    if shutil.disk_usage(root).free < 2*1024**3:
        return save_summary(root, summary(db, now, 'PAUSED_LOW_DISK'))
    # Cap added research storage, without deleting user data or evidence.
    pages = db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0]
    if pages > 512*1024**2: return save_summary(root, summary(db, now, 'PAUSED_STORAGE_BUDGET'))
    cursor = db.execute('SELECT cursor FROM lab_progress WHERE id=1').fetchone()[0]
    symbol = names[cursor % len(names)]
    emit('HISTORY','STARTED',symbol=symbol)
    offset, complete = db.execute('SELECT history_offset,history_complete FROM lab_universe WHERE symbol=?',(symbol,)).fetchone()
    try:
        broker.symbol_select(symbol, True)
        # Always refresh recent closed bars; then advance one bounded historical chunk.
        blocks = [broker.copy_rates_from_pos(symbol, broker.TIMEFRAME_H1, 1, CHUNK)]
        if offset > 1 and not complete:
            blocks.append(broker.copy_rates_from_pos(symbol, broker.TIMEFRAME_H1, offset, CHUNK))
        valid = []
        for block in blocks:
            if block is None: continue
            for r in block:
                stamp = int(r['time'])
                v = tuple(float(r[k]) for k in ('open','high','low','close'))
                # Broker wall-clock is retained as raw, never advertised as UTC.
                if stamp <= 0 or not all(math.isfinite(x) and x>0 for x in v) or not v[2] <= min(v[0],v[3]) <= max(v[0],v[3]) <= v[1]: continue
                valid.append((symbol,stamp,*v))
        with db:
            db.executemany('INSERT OR IGNORE INTO lab_bars VALUES(?,?,?,?,?,?)',valid)
            last = blocks[-1]
            if last is not None:
                done = len(last)<CHUNK or offset+CHUNK >= MAX_HISTORY
                db.execute('UPDATE lab_universe SET history_offset=?,history_complete=?,status=? WHERE symbol=?',
                           (min(MAX_HISTORY,offset+CHUNK),int(done),'HISTORY_COLLECTING' if valid else 'DATA_UNAVAILABLE',symbol))
        emit('HISTORY','DONE',symbol=symbol,count=len(valid))
        rows = db.execute('SELECT stamp,o,h,l,c FROM lab_bars WHERE symbol=? ORDER BY stamp DESC LIMIT 8192',(symbol,)).fetchall()[::-1]
        if len(rows)>=512:
            digest=sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
            ident=sha256((VERSION+symbol+digest).encode()).hexdigest()
            if not db.execute('SELECT 1 FROM lab_runs WHERE id=?',(ident,)).fetchone():
                emit('EXPERIMENT','STARTED',symbol=symbol)
                cost=typical_spread(broker,symbol,blocks[0])
                if cost is not None:
                    spread=cost['price']
                    ratio,prohibitive=cost_gate(rows,spread)
                    result=evaluate(rows,spread)
                    result.update(spread_source=cost['source'],spread_samples=cost['samples'],
                                  current_quote_spread=cost['current_quote'],
                                  spread_to_median_range=round(ratio,6) if ratio is not None else None,
                                  cost_prohibitive=prohibitive)
                    result.update(version=VERSION,spread_proxy_price=spread,gap_intervals=sum(b[0]-a[0]!=3600 for a,b in zip(rows,rows[1:])),bars=len(rows),first_raw_broker_stamp=rows[0][0],last_raw_broker_stamp=rows[-1][0],data_sha256=digest)
                    with db:
                        db.execute('INSERT INTO lab_runs VALUES(?,?,?,?,?)',(ident,symbol,now.isoformat(),digest,json.dumps(result,allow_nan=False)))
                        db.execute('UPDATE lab_universe SET status=? WHERE symbol=?',
                                   ('COST_PROHIBITIVE' if prohibitive else 'EXPLORATORY_ONLY',symbol))
                    emit('EXPERIMENT','DONE',symbol=symbol,count=6)
                else: emit('EXPERIMENT','FAILED',symbol=symbol)
    except Exception:
        emit('HISTORY','FAILED',symbol=symbol)
        with db: db.execute("UPDATE lab_universe SET status='RETRY_PENDING' WHERE symbol=?",(symbol,))
    with db: db.execute('UPDATE lab_progress SET cursor=cursor+1 WHERE id=1')
    result=summary(db,now,'RUNNING')
    return save_summary(root,result)


def save_summary(root,result):
    target=Path(root)/'research-lab.json'; temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(result,allow_nan=False)+'\n',encoding='utf-8');temp.replace(target)
    return result


def summary(db, now, status):
    rows=db.execute('SELECT id,symbol,created_utc,result_json FROM lab_runs ORDER BY created_utc DESC,id DESC LIMIT 24').fetchall()
    return dict(schema_version=1,status=status,as_of_utc=now.isoformat(),
        universe_count=db.execute('SELECT COUNT(*) FROM lab_universe').fetchone()[0],
        scanned_count=db.execute('SELECT COUNT(*) FROM lab_universe WHERE scan_utc IS NOT NULL').fetchone()[0],
        history_symbols=db.execute('SELECT COUNT(DISTINCT symbol) FROM lab_bars').fetchone()[0],
        history_bars=db.execute('SELECT COUNT(*) FROM lab_bars').fetchone()[0],
        experiments=db.execute('SELECT COUNT(*) FROM lab_runs').fetchone()[0],
        strategy_candidates=db.execute('SELECT COUNT(*)*6 FROM lab_runs').fetchone()[0],
        live_authorized=False,improvement_verified=False,
        recent=[dict(id=r[0],symbol=r[1],created_utc=r[2],result=json.loads(r[3])) for r in rows])
