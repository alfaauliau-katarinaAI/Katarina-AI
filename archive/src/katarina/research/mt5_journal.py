"""Strict adapter from MT5 research journals to chronological offline AI samples.

Clock values use the broker's wall-clock axis, NOT verified UTC. Minute timestamps
are intervals: entry uses its lower bound and exit its upper bound for purging.
Only pre-entry measurements become predictors; outcomes never become features.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import StringIO
from math import isfinite, tanh
from pathlib import Path

from katarina.intelligence.brain import LabeledMarketExample

FEATURE_NAMES = (
    'side', 'rsi_norm', 'adx_norm', 'atr_pct_tanh', 'ema_slope_atr_tanh',
    'close_fast_atr_tanh', 'close_slow_atr_tanh', 'ref_span_atr_tanh',
    'fib_retrace_tanh', 'sweep_pen_atr_tanh', 'spread_atr_tanh',
)
NUMERIC = ('rsi', 'adx', 'atr_pct', 'ema_slope_atr', 'close_fast_atr',
           'close_slow_atr', 'ref_span_atr', 'fib_retrace', 'sweep_pen_atr', 'spread_atr')
REQUIRED = {'run_tag', 'entry_time', 'exit_time', 'side', 'net_profit', 'win', *NUMERIC}


@dataclass(frozen=True)
class JournalDataset:
    rows: tuple[LabeledMarketExample, ...]
    net_profits: tuple[Decimal, ...]
    sides: tuple[str, ...]
    source_sha256: str


def _clock(text: str, *, upper: bool) -> int:
    # Treat server-clock dates as coordinates; do not assert an actual UTC offset.
    for fmt, resolution in (('%Y.%m.%d %H:%M:%S', 1), ('%Y.%m.%d %H:%M', 60)):
        try:
            parsed = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            if upper:
                parsed += timedelta(seconds=resolution)
            return int(parsed.timestamp()) * 1_000_000_000
        except ValueError:
            continue
    raise ValueError('invalid broker timestamp')


def load_journal(path: Path, *, expected_trades: int, expected_net_profit: Decimal) -> JournalDataset:
    if type(expected_trades) is not int or expected_trades < 1 or not expected_net_profit.is_finite():
        raise ValueError('invalid reconciliation totals')
    raw = path.read_bytes()
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    reader = csv.DictReader(StringIO(raw.decode(encoding)), delimiter=';')
    headers = reader.fieldnames or []
    if len(headers) != len(set(headers)) or not REQUIRED.issubset(headers):
        raise ValueError('missing or duplicate journal columns')
    items = []; seen = set(); runs = set()
    for line, row in enumerate(reader, 2):
        try:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('malformed CSV row')
            if row['side'] not in ('BUY', 'SELL') or not row['run_tag'].strip():
                raise ValueError('invalid side/run identity')
            entry = _clock(row['entry_time'], upper=False)
            exit_lower = _clock(row['exit_time'], upper=False)
            if exit_lower < entry:
                raise ValueError('exit precedes entry')
            known = _clock(row['exit_time'], upper=True)
            values = [float(row[key]) for key in NUMERIC]
            if not all(isfinite(value) for value in values):
                raise ValueError('non-finite feature')
            rsi, adx, atr, slope, fast, slow, span, fib, sweep, spread = values
            if not (0 <= rsi <= 100 and 0 <= adx <= 100 and atr > 0 and span > 0 and sweep >= 0 and spread >= 0):
                raise ValueError('feature outside physical bounds')
            profit = Decimal(row['net_profit'])
            if not profit.is_finite() or row['win'] not in ('0', '1') or int(row['win']) != int(profit > 0):
                raise ValueError('invalid or inconsistent outcome label')
            identity = sha256(f"{row['run_tag']}|{entry}|{row['side']}".encode()).hexdigest()
            if identity in seen:
                raise ValueError('duplicate trade observation')
            seen.add(identity); runs.add(row['run_tag'])
            vector = (1.0 if row['side'] == 'BUY' else -1.0, rsi / 100, adx / 100,
                      tanh(atr), tanh(slope), tanh(fast), tanh(slow), tanh(span / 10),
                      tanh(fib), tanh(sweep), tanh(spread))
            items.append((LabeledMarketExample(identity, entry, known, vector, int(profit > 0)), profit, row['side']))
        except (ValueError, InvalidOperation, OverflowError) as exc:
            raise ValueError(f'journal line {line}: {exc}') from exc
    if len(runs) != 1:
        raise ValueError('one journal run required; do not pool repeated backtests')
    if len(items) != expected_trades:
        raise ValueError('trade count does not reconcile with MT5 report')
    # The journal rounds each trade to cents; allow half a cent per row.
    tolerance = Decimal('0.005') * len(items)
    if abs(sum((item[1] for item in items), Decimal(0)) - expected_net_profit) > tolerance:
        raise ValueError('net profit does not reconcile; check missing trades or entry costs')
    items.sort(key=lambda item: (item[0].observed_ns, item[0].sample_id))
    return JournalDataset(tuple(x[0] for x in items), tuple(x[1] for x in items),
                          tuple(x[2] for x in items), sha256(raw).hexdigest())
