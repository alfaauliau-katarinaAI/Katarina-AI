"""Additional official news for research only, never policy/trading clearance."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
import re
from urllib.error import HTTPError
import ssl
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
import xml.etree.ElementTree as ET
from katarina.intelligence.news.verified_policy_context import _Paragraphs

SOURCES = {
    'fed': ('https://www.federalreserve.gov/feeds/press_all.xml', 'www.federalreserve.gov'),
    'ecb': ('https://www.ecb.europa.eu/rss/press.html', 'www.ecb.europa.eu'),
    'boc': ('https://www.bankofcanada.ca/content_type/press-releases/feed/', 'www.bankofcanada.ca'),
    'rba': ('https://www.rba.gov.au/rss/rss-cb-media-releases.xml', 'www.rba.gov.au'),
}


def allowed(url, host):
    try:
        p=urlsplit(url)
        return (p.scheme=='https' and p.hostname==host and p.port in (None,443)
                and not p.username and not p.password and not p.query and not p.fragment)
    except ValueError:
        return False


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('research_news_redirect_rejected')


def fetch(url, host):
    if not allowed(url,host):raise ValueError('research_news_host_rejected')
    try:
        import certifi
        context=ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context=ssl.create_default_context()
    with build_opener(NoRedirect(),HTTPSHandler(context=context)).open(Request(url,headers={'User-Agent':'KatarinaResearch/1.0',
            'Accept':'application/rss+xml,application/xml;q=0.9,text/html;q=0.8,*/*;q=0.5'}),timeout=8) as response:
        raw=response.read(600001)
    if len(raw)>600000:raise ValueError('research_news_size_exceeded')
    return raw


def parse_feed(raw, host, now):
    root=ET.fromstring(raw)
    items=[]
    for element in root.iter():
        if element.tag.split('}')[-1] not in ('item','entry'):continue
        fields={c.tag.split('}')[-1]:c for c in element}
        title=' '.join((fields['title'].text or '').split()) if 'title' in fields else ''
        link=fields.get('link')
        url=(link.get('href') or link.text or '').strip() if link is not None else ''
        if allowed(url,host):
            parts=urlsplit(url)
            url=urlunsplit((parts.scheme,parts.netloc,'/'+parts.path.lstrip('/'),'',''))
        date=next((fields[k].text for k in ('pubDate','published','date','updated') if k in fields),None)
        try:
            try: stamp=parsedate_to_datetime(date)
            except (TypeError,ValueError): stamp=datetime.fromisoformat(date.replace('Z','+00:00'))
            if stamp.tzinfo is None or not 0 <= (now-stamp).total_seconds() <= 14*86400:continue
        except (TypeError,ValueError,AttributeError):continue
        if title and allowed(url,host):items.append(dict(title=title[:500],url=url,published=stamp.astimezone(timezone.utc).isoformat()))
    return sorted(items,key=lambda r:r['published'],reverse=True)[:12]


TOPICS = {
    'RATES_INFLATION': r'\b(inflation|monetary|interest rates?|fomc|discount rate|yields?)\b',
    'EMPLOYMENT_GROWTH': r'\b(employment|payrolls?|unemployment|recession|economic growth|gdp)\b',
    'ENERGY_SUPPLY': r'\b(oil|crude|diesel|opec|brent|energy|gasoline)\b',
    'PRECIOUS_METALS': r'\b(gold|silver|bullion)\b',
    'GEOPOLITICS_TRADE': r'\b(war|tariffs?|sanctions?|geopolitical|trade agreement)\b',
    'TECH_RISK': r'\b(artificial intelligence|semiconductors?|chipmakers?|technology|equities|stocks?)\b',
    'FX': r'\b(dollar|euro|yen|rupee|currenc(?:y|ies)|forex)\b',
}


def describe_body(body):
    """Extract quoted-text context and lexical topics, never generated sentiment."""
    paragraphs=[' '.join(p.split()) for p in body.splitlines() if len(p.split())>=12
                and not re.search(r'cookie|all rights reserved|subscribe|privacy policy',p,re.I)]
    text=' '.join(paragraphs) if paragraphs else ' '.join(body.split())
    topics=[name for name,pattern in TOPICS.items() if re.search(pattern,text,re.I)]
    sentences=re.split(r'(?<=[.!?])\s+',text)
    ranked=sorted(enumerate(sentences),key=lambda item:(
        -sum(bool(re.search(pattern,item[1],re.I)) for pattern in TOPICS.values()),item[0]))
    selected=sorted(ranked[:3])
    summary=' '.join(sentence for _,sentence in selected)
    return dict(topics=topics or ['OTHER'],extractive_summary=' '.join(summary.split()[:120]),
                method='LEXICAL_TOPICS_AND_EXTRACTIVE_SENTENCES',
                sentiment='NOT_INFERRED',semantic_interpretation_verified=False)


def collect(db, now, *, exchange=None):
    from katarina.intelligence.news.research_agenda import prioritize, record_leads, status as agenda_status
    exchange=exchange or fetch
    db.execute('''CREATE TABLE IF NOT EXISTS research_news_fetches(source TEXT PRIMARY KEY,
        attempted_epoch REAL NOT NULL,status TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS research_news_documents(
        id TEXT PRIMARY KEY,source TEXT NOT NULL,url TEXT NOT NULL,published TEXT NOT NULL,
        known_utc TEXT NOT NULL,body TEXT NOT NULL,body_sha256 TEXT NOT NULL,summary TEXT NOT NULL)''')
    new=[]
    tables={r[0] for r in db.execute('SELECT name FROM sqlite_master WHERE type=?',('table',))}
    cached=[]
    if 'contextual_market_articles' in tables:
        cached.extend(('cnbc',url,published,known,body,digest) for url,published,body,known,digest in db.execute(
            'SELECT url,published,body,fetched,sha256 FROM contextual_market_articles ORDER BY fetched DESC LIMIT 24'))
    if 'contextual_official_articles' in tables:
        cached.extend(db.execute('SELECT source,url,published,observed,body,body_digest FROM contextual_official_articles ORDER BY observed DESC LIMIT 24'))
    for source,url,published,known,body,digest in cached:
        try:
            p,k=datetime.fromisoformat(published),datetime.fromisoformat(known)
            if p.tzinfo is None or k.tzinfo is None or not p<=k<=now or sha256(body.encode()).hexdigest()!=digest:continue
            ident=sha256(url.encode()).hexdigest()
            summary=describe_body(body)['extractive_summary']
            with db:
                db.execute('INSERT OR IGNORE INTO research_news_documents VALUES(?,?,?,?,?,?,?,?)',
                    (ident,source,url,published,known,body,digest,summary))
                inserted=db.execute('SELECT changes()').fetchone()[0]
            if inserted:new.append(dict(id=ident,source=source,url=url,published_utc=published,
                known_utc=known,body_sha256=digest,extractive_summary=summary,
                topics=describe_body(body)['topics'],semantic_interpretation_verified=False))
        except (ValueError,TypeError,AttributeError):continue
    candidates=[]
    for source in SOURCES:
        row=db.execute('SELECT attempted_epoch,status FROM research_news_fetches WHERE source=?',(source,)).fetchone()
        retry_after=300 if row and row[1].startswith(('HTTP_','UNAVAILABLE_')) else 1800
        if row is None or now.timestamp()-row[0]>=retry_after:candidates.append((row[0] if row else 0,source))
    status='CACHED';source=None
    if candidates:
        _,source=min(candidates)
        url,host=SOURCES[source]
        try:
            stories=prioritize(db,parse_feed(exchange(url,host),host,now))
            status='NO_NEW_ARTICLE'
            for story in stories:
                ident=sha256(story['url'].encode()).hexdigest()
                if db.execute('SELECT 1 FROM research_news_documents WHERE id=?',(ident,)).fetchone():continue
                parser=_Paragraphs();parser.feed(exchange(story['url'],host).decode('utf-8','replace'))
                body='\n'.join(parser.paragraphs)
                if len(body.split())<95:raise ValueError('full_research_article_unavailable')
                known=datetime.now(timezone.utc)
                digest=sha256(body.encode()).hexdigest()
                summary=describe_body(body)['extractive_summary']
                with db:
                    db.execute('INSERT OR IGNORE INTO research_news_documents VALUES(?,?,?,?,?,?,?,?)',
                        (ident,source,story['url'],story['published'],known.isoformat(),body,digest,summary))
                new.append(dict(id=ident,source=source,url=story['url'],published_utc=story['published'],
                    known_utc=known.isoformat(),body_sha256=digest,extractive_summary=summary,
                    topics=describe_body(body)['topics'],semantic_interpretation_verified=False))
                record_leads(db,ident,body,known.isoformat())
                status='FULL_BODY_STORED'
                break
        except HTTPError as exc:
            status='HTTP_'+str(exc.code)
        except Exception as exc:
            status='UNAVAILABLE_'+type(exc).__name__
        with db:
            db.execute('INSERT OR REPLACE INTO research_news_fetches VALUES(?,?,?)',(source,now.timestamp(),status))
    total=db.execute('SELECT COUNT(*) FROM research_news_documents').fetchone()[0]
    return dict(source_checked=source,status=status,new_documents=new,total_documents=total,
                autonomous_agenda=agenda_status(db),
                source_count=len(SOURCES),source_statuses={r[0]:r[1] for r in db.execute(
                    'SELECT source,status FROM research_news_fetches')},
                document_contexts=[dict(id=ident,source=src,known_utc=known,**describe_body(body),
                    paragraph_ids=[sha256(p.strip().encode()).hexdigest() for p in body.splitlines() if len(p.split())>=12][:8])
                    for ident,src,known,body in db.execute(
                        'SELECT id,source,known_utc,body FROM research_news_documents ORDER BY known_utc DESC LIMIT 48')],
                scope='AUXILIARY_RESEARCH_NO_MACRO_CLEARANCE',
                model_summary_available=False,live_execution_authorized=False)


def event_study(db, now):
    """Observed reactions after actual local retrieval, never historical backdating."""
    tables={r[0] for r in db.execute('SELECT name FROM sqlite_master WHERE type=?',('table',))}
    if not {'research_news_documents','research_market_samples'}<=tables:
        return dict(status='WAITING_FOR_DATA',groups=[],causality_proven=False)
    symbols=[r[0] for r in db.execute('SELECT DISTINCT symbol FROM research_market_samples ORDER BY symbol LIMIT 17')]
    db.execute('''CREATE TABLE IF NOT EXISTS research_news_reactions(
        document_id TEXT NOT NULL,source TEXT NOT NULL,symbol TEXT NOT NULL,
        horizon_seconds INTEGER NOT NULL,start_epoch REAL NOT NULL,end_epoch REAL NOT NULL,
        mid_return_bps REAL NOT NULL,topics_json TEXT NOT NULL,
        PRIMARY KEY(document_id,symbol,horizon_seconds))''')
    db.execute('''CREATE TABLE IF NOT EXISTS research_news_topic_reactions(
        document_id TEXT NOT NULL,topic TEXT NOT NULL,symbol TEXT NOT NULL,
        horizon_seconds INTEGER NOT NULL,mid_return_bps REAL NOT NULL,
        PRIMARY KEY(document_id,topic,symbol,horizon_seconds))''')
    pending=missing=0
    for ident,source,known,body,digest in db.execute('SELECT id,source,known_utc,body,body_sha256 FROM research_news_documents ORDER BY known_utc DESC LIMIT 48'):
        if sha256(body.encode()).hexdigest()!=digest:raise ValueError('research_news_digest_mismatch')
        stamp=datetime.fromisoformat(known).timestamp()
        if stamp>now.timestamp():continue
        for symbol in symbols:
            for horizon in (300,900,3600):
                due=stamp+horizon
                if due>now.timestamp():pending+=1;continue
                start=db.execute('''SELECT tick_epoch,mid FROM research_market_samples WHERE symbol=? AND
                    tick_epoch>=? AND tick_epoch<=? AND observed_epoch<=? ORDER BY tick_epoch LIMIT 1''',
                    (symbol,stamp,stamp+180,min(now.timestamp(),stamp+180))).fetchone()
                end=db.execute('''SELECT tick_epoch,mid FROM research_market_samples WHERE symbol=? AND
                    tick_epoch>=? AND tick_epoch<=? AND observed_epoch<=? ORDER BY tick_epoch LIMIT 1''',
                    (symbol,due,due+180,min(now.timestamp(),due+180))).fetchone()
                if not start or not end:
                    if now.timestamp()<due+180:pending+=1
                    else:missing+=1
                    continue
                value=(end[1]/start[1]-1)*10000
                topics=describe_body(body)['topics']
                with db:
                    db.execute('INSERT OR IGNORE INTO research_news_reactions VALUES(?,?,?,?,?,?,?,?)',
                        (ident,source,symbol,horizon,start[0],end[0],value,json.dumps(topics)))
                    for topic in topics:
                        db.execute('INSERT OR IGNORE INTO research_news_topic_reactions VALUES(?,?,?,?,?)',
                            (ident,topic,symbol,horizon,value))
    def aggregate(table,dimension):
        return [dict(zip((dimension,'symbol','horizon_seconds','events','mean_mid_return_bps','positive'),r),
            status='EXPLORATORY_NOT_CAUSAL' if r[3]>=20 else 'INSUFFICIENT_EVENTS')
            for r in db.execute(f'SELECT {dimension},symbol,horizon_seconds,COUNT(*),AVG(mid_return_bps),'
                f'SUM(mid_return_bps>0) FROM {table} GROUP BY {dimension},symbol,horizon_seconds '
                f'ORDER BY {dimension},symbol,horizon_seconds')]
    rows=aggregate('research_news_reactions','source')
    topic_rows=aggregate('research_news_topic_reactions','topic')
    stored=db.execute('SELECT COUNT(*) FROM research_news_reactions').fetchone()[0]
    return dict(status='OBSERVATIONAL_EVENT_STUDY',groups=rows,topic_groups=topic_rows,
        stored_reactions=stored,learning_status='WAITING_FOR_MATCHED_QUOTES' if not rows else 'ACCUMULATING_OBSERVED_REACTIONS',
        aggregation_scope='ALL_PERSISTED_MATCHED_EVENTS',new_match_scan_document_limit=48,
        topic_method='LEXICAL_NOT_MODEL_SENTIMENT',minimum_events_per_group=20,pending_windows=pending,
        missing_quote_windows=missing,causality_proven=False,independent_events_verified=False,
        strategy_validated=False,orders_submitted=0,
        time_basis='FIRST_LOCAL_BODY_RETRIEVAL_NOT_HISTORICAL_PUBLIC_RELEASE')
