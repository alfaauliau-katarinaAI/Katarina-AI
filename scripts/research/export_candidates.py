"""WP4: fail-closed research-candidate -> Stage 1 Trade export.

Only pre-13-Oct-2026 candidates, immutable registered hypothesis, and real
broker tick files with ledger SHA256 and no gaps are eligible. A tick archive's
sha256 is computed on the *decompressed CSV bytes* (WP12 contract). No MT5,
broker network, holdout read, orders or strategy tuning is performed.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.research.dev_dataset import DEV_CUTOFF_UTC  # noqa: E402
from katarina.research.validation import (  # noqa: E402
    HypothesisRegistry, Trade, ValidationError, canonical,
)
from katarina.research.setups.simulator import trade_to_dict  # noqa: E402

MAX_TICKS_PER_DAY = 3_000_000
MAX_CANDIDATES = 400


def _utc(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("naive")
        return result.astimezone(timezone.utc)
    except (AttributeError, ValueError, TypeError) as error:
        raise ValidationError("candidate_timestamp_invalid") from error


def _exit_spec(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("parameters"), dict):
        raise ValidationError("candidate_hypothesis_invalid")
    p = spec["parameters"]
    if p.get("exit_mode") != "CANDIDATE_LEVELS_TICK_FIRST_TOUCH":
        raise ValidationError("candidate_exit_mode_not_registered")
    for name, minimum, maximum in (
        ("entry_wait_seconds", 1, 300), ("max_hold_seconds", 1, 86400)
    ):
        value = p.get(name)
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValidationError("candidate_exit_parameter_missing_or_invalid:" + name)
    return p


def _frozen_ticks(db, root: Path, symbol: str, day: str):
    row = db.execute(
        "SELECT status, sha256, file, ticks FROM broker_tick_days "
        "WHERE symbol=? AND day=?", (symbol, day)
    ).fetchone()
    if row is None or row[0] != "STORED" or not isinstance(row[1], str):
        raise ValidationError("BROKER_TICKS_NOT_VERIFIED:" + day)
    file = row[2]
    if not isinstance(file, str) or not file or Path(file).is_absolute():
        raise ValidationError("BROKER_TICK_FILE_UNSAFE")
    path = (root / file).resolve()
    if root.resolve() not in path.parents or not path.is_file() or path.is_symlink():
        raise ValidationError("BROKER_TICK_FILE_UNSAFE")
    # Independent bytes verification against the Stage0 tick ledger hash.
    digest = hashlib.sha256()
    try:
        with gzip.open(path, "rb") as f:
            while chunk := f.read(65536):
                digest.update(chunk)
    except (OSError, EOFError) as error:
        raise ValidationError("BROKER_TICK_ARCHIVE_INVALID") from error
    if digest.hexdigest() != row[1]:
        raise ValidationError("BROKER_TICK_HASH_MISMATCH")
    ticks, last = [], None
    try:
        with gzip.open(path, "rt", encoding="ascii", newline="") as f:
            reader = csv.reader(f)
            if tuple(next(reader)) != ("time_msc", "bid", "ask", "flags"):
                raise ValidationError("BROKER_TICK_HEADER_INVALID")
            for values in reader:
                if len(values) != 4:
                    raise ValidationError("BROKER_TICK_ROW_INVALID")
                msc, bid, ask, flags = int(values[0]), float(values[1]), float(values[2]), int(values[3])
                if (msc < 0 or (last is not None and msc < last)
                    or not all(math.isfinite(v) for v in (bid, ask))
                    or bid <= 0 or ask < bid):
                    raise ValidationError("BROKER_TICK_ROW_INVALID")
                when = datetime.fromtimestamp(msc / 1000, timezone.utc)
                if when.date().isoformat() != day or when >= DEV_CUTOFF_UTC:
                    raise ValidationError("holdout_data_forbidden")
                ticks.append((msc, bid, ask))
                last = msc
                if len(ticks) > MAX_TICKS_PER_DAY:
                    raise ValidationError("BROKER_TICK_ARCHIVE_TOO_LARGE")
    except (OSError, EOFError, UnicodeError, ValueError, StopIteration) as error:
        if isinstance(error, ValidationError):
            raise
        raise ValidationError("BROKER_TICK_ARCHIVE_INVALID") from error
    if type(row[3]) is not int or len(ticks) != row[3]:
        raise ValidationError("BROKER_TICK_COUNT_MISMATCH")
    return ticks


def export_candidates(db, state_root, registry, hypothesis_id, *, max_candidates=MAX_CANDIDATES):
    """Return immutable Trade instances with all costs sourced from verified ticks."""
    if type(max_candidates) is not int or not 1 <= max_candidates <= MAX_CANDIDATES:
        raise ValidationError("candidate_limit_invalid")
    entry = registry.get(hypothesis_id)
    if entry is None:
        raise ValidationError("hypothesis_not_registered")
    spec = entry["spec"]
    p = _exit_spec(spec)
    if spec.get("side") not in ("BUY", "SELL"):
        raise ValidationError("candidate_hypothesis_side_invalid")
    db.execute("PRAGMA query_only=ON")
    available = {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"research_candidates", "broker_tick_days"} <= available:
        raise ValidationError("CANDIDATE_OR_TICK_LEDGER_MISSING")
    raw = db.execute(
        "SELECT cycle_id,symbol,closed_m5_utc,observed_utc,direction_bias,"
        "conditional_side,conditional_invalidation,conditional_target "
        "FROM research_candidates WHERE symbol=? ORDER BY observed_utc,cycle_id LIMIT ?",
        (spec["symbol"], max_candidates+1)
    ).fetchall()
    if len(raw) > max_candidates:
        raise ValidationError("CANDIDATE_EXPORT_LIMIT_REACHED")
    results, skipped, cache, occupied_until = [], {}, {}, None
    root = Path(state_root).resolve()
    for cid, symbol, closed, observed, bias, side, invalid, target in raw:
        if side not in ("BUY", "SELL"):
            side = bias if bias in ("BUY", "SELL") else None
        if side is None or side != spec["side"] or invalid is None or target is None or closed is None:
            skipped["INCOMPLETE_CANDIDATE"] = skipped.get("INCOMPLETE_CANDIDATE", 0) + 1
            continue
        data_until, observed_at = _utc(closed), _utc(observed)
        if observed_at >= DEV_CUTOFF_UTC or data_until >= DEV_CUTOFF_UTC:
            raise ValidationError("holdout_data_forbidden")
        if data_until > observed_at:
            raise ValidationError("CANDIDATE_LOOKAHEAD_FORBIDDEN")
        if occupied_until is not None and observed_at < occupied_until:
            skipped["OVERLAP"] = skipped.get("OVERLAP", 0) + 1
            continue
        try:
            stop, goal = float(invalid), float(target)
        except (TypeError, ValueError) as error:
            raise ValidationError("CANDIDATE_PRICE_INVALID") from error
        if not all(math.isfinite(v) and v > 0 for v in (stop, goal)):
            raise ValidationError("CANDIDATE_PRICE_INVALID")
        start, end = observed_at, observed_at + timedelta(
            seconds=p["entry_wait_seconds"] + p["max_hold_seconds"])
        if end >= DEV_CUTOFF_UTC:
            raise ValidationError("holdout_data_forbidden")
        span = (end.date() - start.date()).days
        timeline = []
        for offset in range(span+1):
            day = (start.date() + timedelta(days=offset)).isoformat()
            key = symbol, day
            if key not in cache:
                cache[key] = _frozen_ticks(db, root, symbol, day)
            timeline.extend(cache[key])
        start_msc = int(start.timestamp()*1000)
        from_tick = next((i for i, tick in enumerate(timeline)
                          if tick[0] >= start_msc), None)
        if from_tick is None or timeline[from_tick][0] > (start + timedelta(
                seconds=p["entry_wait_seconds"])).timestamp()*1000:
            skipped["NO_CAUSAL_ENTRY_TICK"] = skipped.get("NO_CAUSAL_ENTRY_TICK", 0)+1
            continue
        in_msc, in_bid, in_ask = timeline[from_tick]
        entry_mid = (in_bid+in_ask)/2
        distance = entry_mid-stop if side=="BUY" else stop-entry_mid
        if distance <= 0 or (side=="BUY" and goal<=entry_mid) or (side=="SELL" and goal>=entry_mid):
            skipped["INVALID_LEVEL_GEOMETRY"] = skipped.get("INVALID_LEVEL_GEOMETRY",0)+1
            continue
        deadline_msc = in_msc + p["max_hold_seconds"]*1000
        out_tick = None
        for msc,bid,ask in timeline[from_tick+1:]:
            if msc <= in_msc:
                continue
            # At each tick, invalidation takes precedence (most conservative).
            invalidated = bid <= stop if side=="BUY" else ask >= stop
            targeted = bid >= goal if side=="BUY" else ask <= goal
            if invalidated or targeted or msc >= deadline_msc:
                out_tick = msc,bid,ask
                break
        if out_tick is None:
            skipped["EXIT_TICK_MISSING"] = skipped.get("EXIT_TICK_MISSING",0)+1
            continue
        out_msc, out_bid, out_ask = out_tick
        entry_at = datetime.fromtimestamp(in_msc/1000,timezone.utc)
        exit_at = datetime.fromtimestamp(out_msc/1000,timezone.utc)
        if exit_at >= DEV_CUTOFF_UTC:
            raise ValidationError("holdout_data_forbidden")
        trade = Trade(
            trade_id=hashlib.sha256((hypothesis_id+":"+cid).encode("ascii")).hexdigest()[:24],
            side=side, entry_at=entry_at, exit_at=exit_at, known_at=exit_at,
            data_until=data_until, entry_mid=entry_mid,
            exit_mid=(out_bid+out_ask)/2, stop_distance=distance,
            spread_entry=in_ask-in_bid, spread_exit=out_ask-out_bid,
            trend_side=bias if bias in ("BUY","SELL") else None
        )
        results.append(trade)
        occupied_until = exit_at
    return results, skipped


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir",required=True)
    parser.add_argument("--workspace",required=True)
    parser.add_argument("--hypothesis",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args(argv)
    root=Path(args.state_dir).resolve()
    out=Path(args.out).resolve()
    if out.exists() or out.is_symlink() or root == out or root in out.parents:
        raise ValidationError("CANDIDATE_OUTPUT_UNSAFE")
    registry=HypothesisRegistry(Path(args.workspace)/"registry.jsonl")
    db_path=root/"context.sqlite3"
    if not db_path.is_file() or db_path.is_symlink():
        raise ValidationError("CANDIDATE_DB_MISSING")
    with sqlite3.connect(db_path.as_uri()+"?mode=ro",uri=True) as db:
        try:
            trades, skipped=export_candidates(db,root,registry,args.hypothesis)
        finally:
            db.close()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("".join(canonical(trade_to_dict(t))+"\n" for t in trades),
                   encoding="utf-8",newline="\n")
    print(json.dumps({"status":"DEVELOPMENT_RESEARCH_ONLY","trades":len(trades),
                      "skipped":skipped,"live_execution_authorized":False},
                     sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
