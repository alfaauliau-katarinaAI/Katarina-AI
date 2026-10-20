"""Export an allowlisted research memory snapshot; never copy the private DB.

No network, broker calls, account IDs, symbol names, prices or credentials.
Output is a portable research ledger, not a replacement for the private dataset.
"""
import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

METHODS={'MOMENTUM','MEAN_REVERSION','BREAKOUT'}
STATUSES={'INSUFFICIENT_SAMPLES','REJECTED_IN_HISTORICAL_REVIEW','NEEDS_FORWARD_VALIDATION','DATASET_CHANGED_REVIEW_UNAVAILABLE'}

def encode(row):
    return json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n'

def snapshot(root, destination):
    source=Path(root)/'experiment-jobs.sqlite3'
    output=Path(destination);output.mkdir(parents=True,exist_ok=True)
    records=[];reviews=[];hypotheses=[];repairs=[];reports=[];counts=Counter();datasets=0
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
        db.execute('BEGIN')  # one consistent read snapshot across all three tables
        for ident,symbol,digest,stamp,raw in db.execute('SELECT id,symbol,digest,created_utc,result_json FROM trials ORDER BY created_utc,id'):
            value=json.loads(raw)
            method=value.get('method');status=value.get('status')
            if method not in METHODS or status not in STATUSES:continue
            record=dict(id=ident,instrument_id=sha256(str(symbol).encode()).hexdigest(),dataset_sha256=digest,created_utc=stamp,
                        method=method,status=status,live_authorized=False,improvement_verified=False)
            for key,allowed in [('side',{'BUY','SELL'}),('lookback',{12,24,48}),('horizon',{4,12,24}),('threshold',{.5,1,1.5})]:
                if value.get(key) in allowed:record[key]=value[key]
            # Dimensionless research measurements only; no spread or monetary/account fields.
            for part in ('development','review'):
                metrics=value.get(part,{})
                record[part]={k:metrics[k] for k in ('n','mean_range_units','win_rate','profit_factor')
                              if k in metrics and (metrics[k] is None or type(metrics[k]) in (int,float))}
            records.append(record);counts[status]+=1
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'research_reports' in tables:
            for ident,trial,stamp,decision,raw in db.execute('SELECT id,trial_id,created_utc,decision,report_json FROM research_reports ORDER BY created_utc,id'):
                if decision not in ('CANDIDATE_FORWARD','AWAITING_COST_REVIEWS','REJECTED','INSUFFICIENT_EVIDENCE','REVIEW_BLOCKED'):continue
                reports.append(dict(id=ident,trial_id=trial,created_utc=stamp,decision=decision,live_authorized=False,production_approved=False))
        if 'research_datasets' in tables:
            datasets=db.execute('SELECT COUNT(*) FROM research_datasets').fetchone()[0]
        if 'research_repairs' in tables:
            for ident,stamp,raw in db.execute('SELECT id,created_utc,result_json FROM research_repairs ORDER BY created_utc,id'):
                value=json.loads(raw)
                if value.get('action')!='RESTORED_EXACT_DATASET_REVIEW' or value.get('new_status') not in STATUSES:continue
                repairs.append(dict(id=ident,created_utc=stamp,action='RESTORED_EXACT_DATASET_REVIEW',
                                    new_status=value['new_status'],live_authorized=False))
        if 'stress_reviews' in tables:
            for ident,stamp,raw in db.execute('SELECT trial_id,created_utc,result_json FROM stress_reviews ORDER BY created_utc,trial_id'):
                value=json.loads(raw)
                if value.get('status') not in STATUSES:continue
                reviews.append(dict(trial_id=ident.removeprefix('COST3:'),cost_multiplier=3 if ident.startswith('COST3:') else 2,
                                    created_utc=stamp,status=value['status'],live_authorized=False))
        if 'gemini_hypotheses' in tables:
            # Hypotheses are generated from public generic prompts only; retain the hash,
            # not unvalidated free text, in the GitHub-safe memory ledger.
            for stamp,raw in db.execute('SELECT created_utc,result_json FROM gemini_hypotheses ORDER BY created_utc'):
                hypotheses.append(dict(created_utc=stamp,content_sha256=sha256(raw.encode()).hexdigest(),
                                       status='PUBLIC_HYPOTHESIS_RECORDED_NOT_IMPLEMENTED',live_authorized=False))
    files={'experiments.jsonl':records,'cost-reviews.jsonl':reviews,'hypotheses.jsonl':hypotheses,'repairs.jsonl':repairs,'decision-reports.jsonl':reports}
    digests={}
    for name,rows in files.items():
        data=''.join(encode(row) for row in rows)
        temporary=output/(name+'.tmp');temporary.write_text(data,encoding='utf-8',newline='\n');temporary.replace(output/name)
        digests[name]=sha256(data.encode('utf-8')).hexdigest()
    stamps=[r['created_utc'] for rows in files.values() for r in rows]
    manifest=dict(schema_version=1,source='PERSISTED_RESEARCH_ALLOWLIST_EXPORT',as_of_utc=max(stamps,default=None),
                  experiments=len(records),cost_reviews=len(reviews),hypotheses=len(hypotheses),assessments=dict(counts),
                  preserved_dataset_count=datasets,repaired_reviews=len(repairs),decision_report_revisions=len(reports),
                  file_sha256=digests,live_authorized=False,full_private_memory_backup=False,
                  excluded=['raw_market_data','account_data','credentials','symbol_names','hypothesis_free_text'])
    temporary=output/'manifest.json.tmp';temporary.write_text(encode(manifest),encoding='utf-8',newline='\n');temporary.replace(output/'manifest.json')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();print(encode(snapshot(args.state_dir,args.output)),end='')
