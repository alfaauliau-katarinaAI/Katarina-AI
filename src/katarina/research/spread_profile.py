"""Broker spread profile from verified tick files (docs/ROADMAP.md WP10a).

Read-only analysis of Stage 0 broker tick files. Calculates time-weighted spread profile (last quote
per UTC minute) per symbol x UTC hour (0-23) and overall symbol summary.

This module is DESCRIPTIVE ONLY and NOT FOR TUNING strategy parameters or models.
No broker access, no orders, no live authority.
"""
from __future__ import annotations

import contextlib
import datetime
import math
import sqlite3
from pathlib import Path

from katarina.research import validation as v
from katarina.research.context_export import USABLE_TICK_DAY_STATUSES, iter_verified_ticks

USAGE = "DESCRIPTIVE_ONLY_NOT_FOR_TUNING"
LABEL = "DESKRIPTIF — data forward, bukan untuk penyetelan"
TOOL = "katarina.research.spread_profile"


def nearest_rank_percentile(sorted_vals: list[float], p: float) -> float:
    """Calculate nearest-rank percentile value for p in [0, 100]."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    rank = math.ceil((p / 100.0) * n)
    idx = max(0, min(rank - 1, n - 1))
    return sorted_vals[idx]


def _compute_stats(spreads: list[float]) -> dict:
    if not spreads:
        return {"minutes": 0, "p50": 0.0, "p90": 0.0, "p99": 0.0, "max": 0.0}
    sorted_s = sorted(spreads)
    return {
        "minutes": len(sorted_s),
        "p50": nearest_rank_percentile(sorted_s, 50.0),
        "p90": nearest_rank_percentile(sorted_s, 90.0),
        "p99": nearest_rank_percentile(sorted_s, 99.0),
        "max": sorted_s[-1],
    }


def build_spread_profile(state_dir: str | Path, since: str, until: str) -> dict:
    """Build broker spread profile report for usable tick days in [since, until] inclusive.

    ``state_dir`` contains context.sqlite3 and broker-ticks/ directory.
    ``since`` and ``until`` are ISO date strings (YYYY-MM-DD).
    """
    try:
        since_date = datetime.datetime.strptime(since, "%Y-%m-%d").date()
        until_date = datetime.datetime.strptime(until, "%Y-%m-%d").date()
    except ValueError:
        raise v.ValidationError("INVALID_DATE_FORMAT")
    if since_date > until_date:
        raise v.ValidationError("INVALID_DATE_RANGE")

    root = Path(state_dir)
    db_path = root / "context.sqlite3"
    if not db_path.exists():
        raise v.ValidationError("OBSERVER_DATABASE_NOT_FOUND")

    placeholders = ",".join("?" for _ in USABLE_TICK_DAY_STATUSES)
    query = f"""
        SELECT symbol, day, status, sha256, file
        FROM broker_tick_days
        WHERE status IN ({placeholders})
          AND day >= ? AND day <= ?
        ORDER BY symbol, day
    """
    params = list(USABLE_TICK_DAY_STATUSES) + [since_date.isoformat(), until_date.isoformat()]

    sources = []
    symbol_records: dict[str, list[dict]] = {}

    with contextlib.closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as db:
        for row in db.execute(query, params):
            sym, day, status, sha256, file_rel = row[0], row[1], row[2], row[3], row[4]
            rec = {"symbol": sym, "day": day, "status": status, "sha256": sha256, "file": file_rel}
            if sym not in symbol_records:
                symbol_records[sym] = []
            symbol_records[sym].append(rec)
            sources.append({"symbol": sym, "day": day, "sha256": sha256})

    symbols_data = {}
    for sym, records in symbol_records.items():
        minute_quotes: dict[int, float] = {}
        for rec in records:
            for time_msc, bid, ask in iter_verified_ticks(root, rec):
                minute_idx = time_msc // 60_000
                minute_quotes[minute_idx] = ask - bid

        hourly_spreads: dict[int, list[float]] = {h: [] for h in range(24)}
        for minute_idx, spread in minute_quotes.items():
            dt = datetime.datetime.fromtimestamp((minute_idx * 60), datetime.timezone.utc)
            hourly_spreads[dt.hour].append(spread)

        hourly_results = {}
        for h in range(24):
            hourly_results[str(h)] = _compute_stats(hourly_spreads[h])

        summary_results = _compute_stats(list(minute_quotes.values()))

        symbols_data[sym] = {
            "summary": summary_results,
            "hourly": hourly_results,
        }

    report = {
        "schema_version": 1,
        "tool": TOOL,
        "usage": USAGE,
        "label": LABEL,
        "period": {
            "since": since_date.isoformat(),
            "until": until_date.isoformat(),
        },
        "sources": sources,
        "symbols": symbols_data,
        "live_execution_authorized": False,
    }
    return report
