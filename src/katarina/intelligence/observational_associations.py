"""Price/news associations independent of entry signals. Never strategy clearance."""
from datetime import datetime, timezone
from hashlib import sha256
import math


def pearson(rows, minimum=20):
    if len(rows) < minimum:
        return dict(n=len(rows), pearson=None, status='INSUFFICIENT_SAMPLES')
    x, y = zip(*rows)
    mx, my = sum(x)/len(x), sum(y)/len(y)
    xx, yy = sum((v-mx)**2 for v in x), sum((v-my)**2 for v in y)
    if xx <= 0 or yy <= 0:
        return dict(n=len(rows), pearson=None, status='NO_VARIATION')
    value = sum((a-mx)*(b-my) for a,b in rows)/math.sqrt(xx*yy)
    return dict(n=len(rows), pearson=round(max(-1., min(1.,value)),6),
                status='EXPLORATORY_ASSOCIATION_ONLY')


def observe_associations(db, quotes, now):
    """Called by the existing brain, using already received past-only quotes."""
    if now.tzinfo is None:
        raise ValueError('aware_clock_required')
    epoch = now.timestamp()
    db.execute('''CREATE TABLE IF NOT EXISTS research_market_samples(
        symbol TEXT NOT NULL, tick_epoch REAL NOT NULL, observed_epoch REAL NOT NULL,
        mid REAL NOT NULL, PRIMARY KEY(symbol,tick_epoch))''')
    with db:
        for symbol, (bid, ask, stamp) in quotes.items():
            if (not all(type(v) in (int,float) and math.isfinite(v) for v in (bid,ask,stamp))
                    or not 0 < bid <= ask or not epoch-180 <= stamp <= epoch):
                raise ValueError('invalid_research_quote')
            db.execute('INSERT OR IGNORE INTO research_market_samples VALUES(?,?,?,?)',
                       (symbol,stamp,epoch,(bid+ask)/2))
    news_times, rejected_news = [], 0
    if db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',
                  ('table','contextual_market_articles')).fetchone():
        for published,fetched,body,digest in db.execute('''SELECT published,fetched,body,sha256
                FROM contextual_market_articles ORDER BY fetched DESC LIMIT 2000'''):
            try:
                p, f = datetime.fromisoformat(published), datetime.fromisoformat(fetched)
                if (p.tzinfo is None or f.tzinfo is None or not p <= f <= now
                        or sha256(body.encode()).hexdigest() != digest):
                    raise ValueError('invalid_news_provenance')
                news_times.append(f.timestamp())
            except (ValueError,TypeError,AttributeError):
                rejected_news += 1
    returns, arrivals = {}, {}
    # At most 17 symbols and 2000 points per symbol. Preserve the full raw ledger.
    symbols = sorted(quotes)
    if len(symbols) > 17:
        raise ValueError('research_symbol_budget_exceeded')
    for symbol in symbols:
        buckets = {}
        rows = db.execute('''SELECT tick_epoch,mid FROM research_market_samples
            WHERE symbol=? AND observed_epoch<=? AND tick_epoch<?
            ORDER BY tick_epoch DESC LIMIT 2000''', (symbol,epoch,int(epoch//300)*300)).fetchall()
        for stamp, mid in rows:
            buckets.setdefault(int(stamp//300), (stamp,mid))
        values, features = {}, {}
        for bucket in sorted(buckets):
            if bucket-1 not in buckets:
                continue
            previous, price = buckets[bucket-1], buckets[bucket]
            values[bucket] = math.log(price[1]/previous[1])
            features[bucket] = sum(previous[0] < t <= price[0] for t in news_times)
        returns[symbol], arrivals[symbol] = values, features
    pairs = []
    for i,a in enumerate(symbols):
        for b in symbols[i+1:]:
            common = sorted(set(returns[a]) & set(returns[b]))
            pairs.append(dict(a=a,b=b,**pearson([(returns[a][t],returns[b][t]) for t in common])))
    news = [dict(symbol=s, **pearson([(arrivals[s][t],abs(value))
            for t,value in returns[s].items()])) for s in symbols]
    return dict(schema_version=1, as_of_utc=now.astimezone(timezone.utc).isoformat(),
        scope='DESCRIPTIVE_RESEARCH_NOT_STRATEGY_PROOF',
        quote_points={s:db.execute('SELECT COUNT(*) FROM research_market_samples WHERE symbol=?',(s,)).fetchone()[0] for s in symbols},
        return_points={s:len(returns[s]) for s in symbols}, price_return_correlations=pairs,
        news_arrival_vs_absolute_return=news, verified_article_times=len(news_times),
        rejected_article_times=rejected_news, minimum_pairs=20,
        live_execution_authorized=False, orders_submitted=0, causal_relationship_proven=False,
        strategy_validated=False,
        limitations=['Completed UTC 5-minute buckets; last quotes are not perfectly synchronous',
                    'Arrival means local first retrieval, not public release time or sentiment',
                    'Shared news exposure, autocorrelation and multiple comparisons remain uncontrolled',
                    'No significance test, predictive claim, P/L or automatic strategy promotion'])
