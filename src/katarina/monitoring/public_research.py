"""Public knowledge topology: stored document provenance, never raw article or MT5 market data."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

SOURCES = frozenset(('fed','ecb','boe','boc','rba','cnbc'))
TOPICS = frozenset(('RATES_INFLATION','EMPLOYMENT_GROWTH','ENERGY_SUPPLY','PRECIOUS_METALS','GEOPOLITICS_TRADE','TECH_RISK','FX','OTHER'))


def identity(kind, raw):
    return kind + ':' + sha256(str(raw).encode('utf-8')).hexdigest()[:24]


def graph_from_report(report):
    news = report.get('research_news') or {}
    nodes, edges, ids, pairs = [], [], set(), set()
    truncated = False
    def add(kind, raw, label, known=None):
        nonlocal truncated
        ident = identity(kind, raw)
        if ident in ids:
            return ident
        if len(nodes) >= 384:
            truncated = True
            return None
        node = dict(id=ident, kind=kind, label=label[:40])
        if known:
            node['known_utc'] = known
        nodes.append(node);ids.add(ident)
        return ident
    def link(a, b, relation):
        nonlocal truncated
        if not a or not b or (a,b,relation) in pairs:
            return
        if len(edges) >= 512:
            truncated = True
            return
        edges.append(dict(a=a,b=b,relation=relation));pairs.add((a,b,relation))
    documents = news.get('document_contexts', [])
    for doc in documents[:48] if isinstance(documents,list) else []:
        if not isinstance(doc,dict) or doc.get('source') not in SOURCES:
            continue
        raw = doc.get('id')
        if not isinstance(raw,str) or not re.fullmatch('[a-f0-9]{64}',raw):
            continue
        try:
            known=datetime.fromisoformat(doc['known_utc'])
            now=datetime.now(timezone.utc)
            if known.tzinfo is None or known > now:
                continue
        except (KeyError,ValueError,TypeError):
            continue
        source=add('source',doc['source'],doc['source'].upper())
        document=add('document',raw,'DOC / '+raw[:8],known.isoformat())
        link(source,document,'RETRIEVED_FROM')
        topics=doc.get('topics',[])
        for topic in topics[:8] if isinstance(topics,list) else []:
            if topic in TOPICS:
                link(add('topic',topic,topic),document,'LEXICAL_TOPIC')
        paragraphs=doc.get('paragraph_ids',[])
        for part in paragraphs[:8] if isinstance(paragraphs,list) else []:
            if isinstance(part,str) and re.fullmatch('[a-f0-9]{64}',part):
                child=add('paragraph',raw+':'+part,'TEXT / '+part[:8],known.isoformat())
                link(document,child,'PART_OF_DOCUMENT')
    links=(report.get('neuro_link_memory') or {}).get('links',[])
    for item in links[:12] if isinstance(links,list) else []:
        if not isinstance(item,dict) or not isinstance(item.get('pattern_key'),str):
            continue
        pattern=add('pattern',item['pattern_key'],'EVIDENCE PATTERN')
        provenance=item.get('provenance_ids',[])
        for raw in provenance[:8] if isinstance(provenance,list) else []:
            if isinstance(raw,str) and len(raw)<=256:
                link(pattern,add('evidence',raw,'STORED EVIDENCE'),'SUPPORTED_BY_RECORD')
    return dict(schema_version=1,source='PERSISTED_RESEARCH_PROVENANCE',
        nodes=nodes,edges=edges,truncated=truncated,
        total_documents=news.get('total_documents') if type(news.get('total_documents')) is int else None,
        semantics='PROVENANCE_AND_LEXICAL_TOPICS_NOT_NEURAL_WEIGHTS',
        neural_activation_measured=False)


def public_entries(report):
    monitor=report.get('broker_account_monitor') or {}
    if not (monitor.get('connected') is True and monitor.get('algo_trading_off') is True
            and monitor.get('positions_read_success') is True):
        return dict(status='NOT_ATTESTED',positions=[])
    positions=[]
    for item in monitor.get('entry_positions',[])[:20]:
        if not isinstance(item,dict):
            continue
        symbol,side,price=item.get('symbol'),item.get('side'),item.get('entry_price')
        if not isinstance(symbol,str) or not re.fullmatch(r'[A-Za-z0-9_.#-]{1,40}',symbol) or side not in ('BUY','SELL'):
            continue
        if type(price) not in (int,float) or not 0 < price < 1e12:
            continue
        try:
            stamp=datetime.fromisoformat(item['opened_utc'])
            if stamp.tzinfo is None or stamp>datetime.now(timezone.utc):
                continue
        except (KeyError,TypeError,ValueError):
            continue
        positions.append(dict(symbol=symbol,side=side,entry_price=price,opened_utc=stamp.isoformat()))
    count=monitor.get('positions_count')
    if positions or count==0:
        return dict(status='OBSERVED',positions=positions,origin='BROKER_BOOK_NOT_ATTRIBUTED_TO_KATARINA',
                    truncated=type(count) is int and count>len(positions))
    return dict(status='NOT_ATTESTED',positions=[])


def read_public_research(root, observation_utc):
    try:
        with (Path(root)/'latest.json').open('rb') as stream:
            raw=stream.read(2_000_001)
        if len(raw)>2_000_000:
            raise ValueError()
        report=json.loads(raw)
        if report.get('observed_at_utc')!=observation_utc:
            raise ValueError()
        stamp=datetime.fromisoformat(observation_utc)
        if stamp.tzinfo is None or not 0 <= (datetime.now(timezone.utc)-stamp).total_seconds()<=180:
            raise ValueError()
        return graph_from_report(report),public_entries(report)
    except (OSError,ValueError,TypeError,AttributeError):
        return (dict(schema_version=1,nodes=[],edges=[],status='NOT_ATTESTED'),
                dict(status='NOT_ATTESTED',positions=[]))
