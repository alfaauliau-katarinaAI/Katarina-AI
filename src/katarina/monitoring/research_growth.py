"""Read-only inventory of real persisted research, independent of the visible graph limit."""
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
import json,sqlite3,time

_cache={}
def read_growth(root,pid):
    root=Path(root);key=(str(root.resolve()),pid);cached=_cache.get(key)
    if cached and time.monotonic()-cached[0]<5:return cached[1]
    unknown={'status':'NOT_ATTESTED'}
    target=root/'experiment-jobs.sqlite3'
    try:
        with closing(sqlite3.connect(target.resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)) as db:
            db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'trials' not in tables:return unknown
            count=lambda table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] if table in tables else 0
            experiments=count('trials');datasets=count('research_datasets');hypotheses=count('gemini_hypotheses');reports=count('research_reports')
            instruments=0
            latest=db.execute("SELECT id,created_utc,json_extract(result_json,'$.method'),json_extract(result_json,'$.side'),json_extract(result_json,'$.horizon'),json_extract(result_json,'$.status') FROM trials ORDER BY rowid DESC LIMIT 1").fetchone()
        docs=0;context=root/'context.sqlite3'
        if context.exists():
            with closing(sqlite3.connect(context.resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)) as db:
                db.execute('PRAGMA query_only=ON')
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='research_news_documents'").fetchone():docs=db.execute('SELECT COUNT(*) FROM research_news_documents').fetchone()[0]
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='lab_universe'").fetchone():instruments=db.execute('SELECT COUNT(*) FROM lab_universe').fetchone()[0]
        value=dict(status='PERSISTED_RESEARCH_COUNTS',pid=pid,as_of_utc=datetime.now(timezone.utc).isoformat(),
            total_nodes=experiments+datasets+instruments+docs,
            experiments=experiments,datasets=datasets,instruments=instruments,documents=docs,
            hypotheses=hypotheses,reports=reports,
            total_files=sum(p.is_file() and p.suffix in ('.json','.jsonl','.sqlite3') for p in root.iterdir()),
            storage='VPS_SQLITE_RECORDS',file_per_node=False,model_training_verified=False,
            semantics='EXPERIMENT_DATASET_INSTRUMENT_DOCUMENT_RECORDS')
        if latest and latest[2] in ('MOMENTUM','MEAN_REVERSION','BREAKOUT') and latest[3] in ('BUY','SELL'):
            value['latest']={'record_id':latest[0],'created_utc':latest[1],'method':latest[2],'side':latest[3],'horizon':latest[4],'status':latest[5]}
        _cache.clear();_cache[key]=(time.monotonic(),value)
        return value
    except (sqlite3.Error,OSError,ValueError,TypeError):return unknown
