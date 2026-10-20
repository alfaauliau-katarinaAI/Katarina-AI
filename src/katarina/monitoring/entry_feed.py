"""Read-only entry history and candidate plans, with explicit provenance and no account fields."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3

from katarina.monitoring.worker_runtime import _read, _fresh


def _stamp(value):
    try:
        t = datetime.fromtimestamp(value, timezone.utc)
        return t.isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _price(value):
    return value if type(value) in (int, float) and math.isfinite(value) and 0 < value < 1e12 else None


def _symbol(value):
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.#-]{1,40}', value) else None


def _db(path):
    db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=.25)
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    return db


def read_entry_feed(root, *, allowed, now=None):
    now = now or datetime.now(timezone.utc)
    root = Path(root)
    empty = dict(status='NOT_ATTESTED', history=[], plans=[])
    executor = _read(root/'demo-forward/executor.json')
    decision = _read(root/'demo-forward/status.json')
    if not (allowed and executor.get('independent') is True and executor.get('mode') == 'DEMO'
            and type(executor.get('pid')) is int and executor['pid'] > 0 and _fresh(executor, now)
            and decision.get('pid') == executor['pid'] and _fresh(decision, now)
            and decision.get('live_authorized') is False):
        return empty
    out = dict(status='OBSERVED', as_of_utc=decision['as_of_utc'], executor_pid=executor['pid'],
               source='KATARINA_DEMO_LEDGER', mode='DEMO', history=[], plans=[],
               history_status='NOT_ATTESTED', plans_status='NOT_ATTESTED', live_authorized=False)
    try:
        with closing(_db(root/'demo-forward/orders.sqlite3')) as orders:
            out['history_total'] = orders.execute("SELECT COUNT(*) FROM demo_outbox WHERE state IN ('OPEN','CLOSED')").fetchone()[0]
            rows = orders.execute("SELECT intent_id,state,updated_at,intent_json,outcome_json FROM demo_outbox WHERE state IN ('OPEN','CLOSED') ORDER BY updated_at DESC,intent_id LIMIT 20").fetchall()
        for ident, state, updated, raw, outcome in rows:
            try:
                intent = json.loads(raw)
                stamp = _stamp(intent.get('created_at'))
                if not (isinstance(ident, str) and _symbol(intent.get('symbol')) and intent.get('side') in ('BUY','SELL')
                        and stamp and -30 <= now.timestamp()-intent['created_at']):
                    continue
                row = dict(id=hashlib.sha256(ident.encode()).hexdigest()[:24], symbol=intent['symbol'],
                           side=intent['side'], state=state, decision_utc=stamp,
                           requested_price=_price(intent.get('price')), stop_loss=_price(intent.get('stop_loss')),
                           take_profit=_price(intent.get('take_profit')), fill_price_verified=False)
                if state == 'CLOSED':
                    closed = json.loads(outcome or '{}')
                    row['closed_observed_utc'] = _stamp(closed.get('closed_observed_at'))
                try:
                    with closing(_db(root/'demo-forward/experiment.sqlite3')) as cache:
                        variant = cache.execute('SELECT report_json FROM demo_variants WHERE id=?',(intent.get('experiment_id'),)).fetchone()
                    params = json.loads(variant[0]).get('parameters',{}) if variant else {}
                    if params.get('method') in ('MOMENTUM','MEAN_REVERSION','BREAKOUT'):
                        row['method'] = params['method']
                    if params.get('horizon') in (4,12,24):
                        row['horizon'] = params['horizon']
                except (sqlite3.Error, OSError, ValueError, TypeError, AttributeError):
                    pass
                out['history'].append(row)
            except (ValueError, TypeError, AttributeError):
                continue
        out['history_status'] = 'OBSERVED'
    except (sqlite3.Error, OSError):
        pass
    try:
        with closing(_db(root/'demo-forward/experiment.sqlite3')) as cache, closing(_db(root/'experiment-jobs.sqlite3')) as research:
            rows = cache.execute('SELECT v.id,v.trial_id,v.report_json,c.last_checked FROM demo_variants v LEFT JOIN demo_candidate_visits c ON c.trial_id=v.trial_id ORDER BY c.last_checked DESC,v.id LIMIT 12').fetchall()
            for ident, trial, raw, checked in rows:
                try:
                    if not re.fullmatch('[a-f0-9]{64}', ident):
                        continue
                    report = json.loads(raw)
                    policy = cache.execute('SELECT report_json FROM demo_policy_reviews WHERE variant_id=? ORDER BY rowid DESC LIMIT 1',(ident,)).fetchone()
                    if policy:
                        report = json.loads(policy[0])
                    params = report.get('parameters') or {}
                    symbol = research.execute('SELECT symbol FROM trials WHERE id=?',(trial,)).fetchone()
                    if not symbol or not _symbol(symbol[0]) or params.get('method') not in ('MOMENTUM','MEAN_REVERSION','BREAKOUT') or params.get('side') not in ('BUY','SELL'):
                        continue
                    if params.get('lookback') not in (12,24,48) or params.get('horizon') not in (4,12,24) or params.get('threshold') not in (.5,1,1.5):
                        continue
                    lesson = cache.execute('SELECT report_json FROM demo_lessons WHERE variant_id=?',(ident,)).fetchone()
                    cooldown = lesson and json.loads(lesson[0]).get('decision') == 'COOLDOWN_RESEARCH_REQUIRED'
                    state = 'COOLDOWN' if cooldown else 'AWAITING_SIGNAL_REVIEW' if report.get('qualified') is True else 'NOT_QUALIFIED'
                    checks = [dict(multiplier=c['multiplier'], passed=c.get('passed') is True) for c in report.get('checks',[]) if isinstance(c,dict) and c.get('multiplier') in (1,2,3)]
                    out['plans'].append(dict(id=ident[:24], symbol=symbol[0], side=params['side'], method=params['method'],
                        lookback=params['lookback'], horizon=params['horizon'], threshold=params['threshold'],
                        state=state, last_reviewed_utc=_stamp(checked), checks=checks,
                        signal_verified=False, executable=False, stop_range=2, target_range=4))
                except (ValueError, TypeError, AttributeError):
                    continue
        out['plans_status'] = 'OBSERVED'
    except (sqlite3.Error, OSError):
        pass
    return out
