"""Stage 0 data ledger: what the observer saw each cycle, and the broker's own ticks.

docs/ROADMAP.md (Tahap 0) keeps two streams apart:

* **Observer snapshots** — one bid/ask/spread row per observed symbol per cycle (WAIT included),
  plus one row per cycle with its outcome and the broker clock shift. This is what Katarina
  "saw" when deciding; it is not tick data.
* **Broker ticks** — every bid/ask tick of a *completed* UTC day, read from MT5 history after
  the day ends, stored as gzip CSV under ``<state>/broker-ticks/<SYMBOL>/<YYYY-MM-DD>.csv.gz``.
  Missing hours are recorded as gaps with a reason and are never interpolated. Stored ticks are
  reconciled against the observer snapshots of the same day (within one tick size).

Only days that the observer itself observed are collected, so backfilled history is never
counted as forward observation. Everything runs inside the canonical owner thread with a bounded
budget; nothing here can send orders.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import math
import os
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA_VERSION = 1
TICK_DIR = "broker-ticks"
# A day is collected only after it is safely over on the broker server as well.
DAY_SETTLE_SECONDS = 2 * 3600
TICK_RETRY_SECONDS = 3600
TICK_MAX_ATTEMPTS = 3
MAX_TICKS_PER_HOUR = 2_000_000
OPEN_CYCLE = "SNAPSHOT_RECORDED"
CYCLE_STATUSES = frozenset(("OK", "PARTIAL", "NO_MARKET_DATA", "FAILED", "ATTEMPT_FAILED"))


def setup(db) -> None:
    db.executescript("""
    CREATE TABLE IF NOT EXISTS observer_cycles(
        cycle_id TEXT PRIMARY KEY,
        observed_utc TEXT NOT NULL,
        finished_utc TEXT,
        status TEXT NOT NULL,
        reason TEXT,
        clock_shift_hours REAL,
        symbols_observed INTEGER NOT NULL DEFAULT 0,
        symbols_with_quote INTEGER NOT NULL DEFAULT 0,
        orders_submitted INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS observer_quotes(
        cycle_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        observed_utc TEXT NOT NULL,
        tick_epoch REAL,
        bid REAL,
        ask REAL,
        spread REAL,
        quote_age_seconds REAL,
        status TEXT NOT NULL,
        reason TEXT,
        UNIQUE(cycle_id, symbol));
    CREATE INDEX IF NOT EXISTS observer_quotes_symbol_day ON observer_quotes(symbol, observed_utc);
    CREATE TABLE IF NOT EXISTS broker_tick_days(
        symbol TEXT NOT NULL,
        day TEXT NOT NULL,
        status TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        next_epoch REAL NOT NULL DEFAULT 0,
        ticks INTEGER NOT NULL DEFAULT 0,
        first_epoch REAL,
        last_epoch REAL,
        sha256 TEXT,
        file TEXT,
        collected_utc TEXT,
        reason TEXT,
        snapshots_checked INTEGER NOT NULL DEFAULT 0,
        snapshots_matched INTEGER NOT NULL DEFAULT 0,
        tick_size REAL,
        PRIMARY KEY(symbol, day));
    CREATE TABLE IF NOT EXISTS reconnect_tests(
        id INTEGER PRIMARY KEY,
        started_utc TEXT NOT NULL,
        method TEXT NOT NULL,
        note TEXT,
        recorded_utc TEXT NOT NULL,
        UNIQUE(started_utc, method));
    CREATE TABLE IF NOT EXISTS data_gaps(
        id INTEGER PRIMARY KEY,
        stream TEXT NOT NULL,
        symbol TEXT,
        start_utc TEXT NOT NULL,
        end_utc TEXT NOT NULL,
        reason TEXT NOT NULL,
        recorded_utc TEXT NOT NULL,
        UNIQUE(stream, symbol, start_utc, end_utc));
    """)
    db.commit()


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("aware_utc_datetime_required")
    return value.astimezone(timezone.utc)


def _finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


# --------------------------------------------------------------------------- observer stream

def record_snapshot(db, *, observed_utc: datetime, clock_shift_hours, cards: dict, quotes: dict) -> str:
    """Store one row per observed symbol (WAIT included) and an open cycle row.

    ``quotes`` maps symbol -> (bid, ask, tick_epoch) exactly as the observer used them;
    ``cards`` maps symbol -> decision card (failed symbols carry ``sensor_reason``).
    Returns the cycle id that :func:`close_cycle` finalizes.
    """
    setup(db)
    observed = _utc(observed_utc)
    stamp = observed.isoformat()
    cycle_id = "c-" + observed.strftime("%Y%m%dT%H%M%S.%fZ")
    with_quote = 0
    rows = []
    for symbol in sorted(cards):
        quote = quotes.get(symbol)
        bid = ask = epoch = None
        if quote is not None:
            bid, ask, epoch = (_finite(v) for v in quote)
        if None not in (bid, ask, epoch) and bid > 0 and ask >= bid:
            with_quote += 1
            rows.append((cycle_id, symbol, stamp, epoch, bid, ask, ask - bid,
                         round(observed.timestamp() - epoch, 3), "OK", None))
        else:
            card = cards.get(symbol) or {}
            reason = str(card.get("sensor_reason") or "QUOTE_NOT_RECORDED")
            rows.append((cycle_id, symbol, stamp, None, None, None, None, None, "FAILED", reason))
    with db:
        db.execute(
            "INSERT INTO observer_cycles(cycle_id, observed_utc, status, clock_shift_hours, "
            "symbols_observed, symbols_with_quote) VALUES(?,?,?,?,?,?)",
            (cycle_id, stamp, OPEN_CYCLE, _finite(clock_shift_hours), len(rows), with_quote))
        db.executemany(
            "INSERT INTO observer_quotes(cycle_id, symbol, observed_utc, tick_epoch, bid, ask, spread, "
            "quote_age_seconds, status, reason) VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
    return cycle_id


def close_cycle(db, *, finished_utc: datetime, cycle_id=None, status: str, reason=None,
                orders_submitted: int = 0) -> str:
    """Finalize the outcome of one observer loop iteration.

    Open snapshots of earlier failed attempts in the same iteration become ``ATTEMPT_FAILED``
    (they are not cycles). Without a snapshot (the pass failed before reading quotes) a
    ``FAILED`` cycle row is inserted so every failure has a recorded reason.
    """
    setup(db)
    if status not in CYCLE_STATUSES - {"ATTEMPT_FAILED"}:
        raise ValueError("invalid_cycle_status")
    finished = _utc(finished_utc).isoformat()
    with db:
        db.execute("UPDATE observer_cycles SET status='ATTEMPT_FAILED', finished_utc=?, "
                   "reason=COALESCE(reason,'ATTEMPT_SUPERSEDED') WHERE status=? AND cycle_id IS NOT ?",
                   (finished, OPEN_CYCLE, cycle_id))
        if cycle_id is None:
            cycle_id = "f-" + _utc(finished_utc).strftime("%Y%m%dT%H%M%S.%fZ")
            db.execute("INSERT OR IGNORE INTO observer_cycles(cycle_id, observed_utc, finished_utc, status, "
                       "reason, orders_submitted) VALUES(?,?,?,?,?,?)",
                       (cycle_id, finished, finished, status, reason, int(orders_submitted)))
        else:
            db.execute("UPDATE observer_cycles SET status=?, reason=?, finished_utc=?, orders_submitted=? "
                       "WHERE cycle_id=?", (status, reason, finished, int(orders_submitted), cycle_id))
    return cycle_id


def cycle_status(result: dict) -> tuple[str, str | None]:
    """Classify an observer result: every observed symbol needs bid/ask for ``OK``."""
    observed = result.get("observed_symbols")
    received = result.get("received_market_data_symbols")
    if type(observed) is not int or type(received) is not int or received <= 0:
        return "NO_MARKET_DATA", "NO_USABLE_MARKET_DATA"
    if received < observed:
        return "PARTIAL", "SOME_SYMBOLS_WITHOUT_QUOTE"
    return "OK", None


RECONNECT_METHODS = frozenset(("KILL_TERMINAL", "KILL_TERMINAL_MID_CYCLE", "NETWORK_DISCONNECT", "VPS_RESTART"))


def record_reconnect_test(db, *, started_utc: datetime, method: str, now: datetime, note: str = "") -> int:
    """Record when a deliberate MT5 disconnect test began; data_health judges the recovery."""
    setup(db)
    if method not in RECONNECT_METHODS:
        raise ValueError("unknown_reconnect_method")
    started, now = _utc(started_utc), _utc(now)
    if started > now:
        raise ValueError("reconnect_test_in_future")
    with db:
        cursor = db.execute("INSERT OR IGNORE INTO reconnect_tests(started_utc, method, note, recorded_utc) "
                            "VALUES(?,?,?,?)", (started.isoformat(), method, str(note)[:200], now.isoformat()))
    return cursor.rowcount


# --------------------------------------------------------------------------- broker tick stream

def tick_path(root, symbol: str, day: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in symbol)
    return Path(root) / TICK_DIR / safe / f"{day}.csv.gz"


def _due_days(db, now: datetime):
    """Observed (symbol, day) pairs whose UTC day is over and not yet settled."""
    # A day is due once day_end + settle time has passed, i.e. it is before this cut-off date.
    cutoff = (now - timedelta(seconds=DAY_SETTLE_SECONDS)).date().isoformat()
    return db.execute(
        "SELECT q.symbol, q.day FROM (SELECT DISTINCT symbol, substr(observed_utc,1,10) AS day "
        "FROM observer_quotes WHERE status='OK' AND observed_utc < ?) q "
        "LEFT JOIN broker_tick_days b ON b.symbol=q.symbol AND b.day=q.day "
        "WHERE b.symbol IS NULL OR (b.status='RETRY' AND b.next_epoch<=?) ORDER BY q.day, q.symbol",
        (cutoff, now.timestamp())).fetchall()


def _record_gap(db, stream, symbol, start: datetime, end: datetime, reason, now: datetime):
    db.execute("INSERT OR IGNORE INTO data_gaps(stream, symbol, start_utc, end_utc, reason, recorded_utc) "
               "VALUES(?,?,?,?,?,?)", (stream, symbol, start.isoformat(), end.isoformat(), reason,
                                       now.isoformat()))


def fx_session_open(moment: datetime) -> bool:
    """Conservative FX trading window in UTC used for Stage 0 statistics.

    Monday 00:00 to Friday 20:00 UTC, excluding the daily rollover 20:45-21:15 UTC. The window is
    deliberately narrower than the real session so that DST shifts never count a closed market
    as a failed cycle.
    """
    moment = _utc(moment)
    if moment.weekday() > 4 or (moment.weekday() == 4 and moment.hour >= 20):
        return False
    minutes = moment.hour * 60 + moment.minute
    return not (20 * 60 + 45 <= minutes < 21 * 60 + 15)


def _download_day(mt5, symbol: str, day_start: datetime, path: Path):
    """Stream one completed broker UTC day; never materialize a whole tick-day.

    Return (count, first_ms, last_ms, CSV_sha256, gaps, hour_index).
    Each index entry stores the *uncompressed* CSV data row boundaries.
    """
    day_start = _utc(day_start)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    gaps, hour_index = [], {}
    count = 0
    first_ms = last_ms = None
    digest = hashlib.sha256()
    flag = getattr(mt5, "COPY_TICKS_ALL", getattr(mt5, "COPY_TICKS_INFO", 0))
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    def flush(archive):
        raw = buffer.getvalue().encode("ascii")
        if raw:
            archive.write(raw)
            digest.update(raw)
            buffer.seek(0)
            buffer.truncate(0)

    try:
        with temp.open("wb") as handle:
            with gzip.GzipFile(filename="", fileobj=handle, mode="wb", mtime=0) as archive:
                writer.writerow(("time_msc", "bid", "ask", "flags"))
                for hour in range(24):
                    start = day_start + timedelta(hours=hour)
                    end = start + timedelta(hours=1)
                    rows = mt5.copy_ticks_range(symbol, start, end, flag)
                    if rows is None:
                        gaps.append((start, end, "BROKER_HISTORY_UNAVAILABLE"))
                        continue
                    if len(rows) > MAX_TICKS_PER_HOUR:
                        gaps.append((start, end, "TICK_HOUR_OVER_LIMIT"))
                        continue
                    lower, upper = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
                    ticks = {}
                    kept = 0
                    for row in rows:
                        try:
                            msc = int(row["time_msc"])
                            bid, ask = float(row["bid"]), float(row["ask"])
                            flags = int(row["flags"]) if "flags" in _names(row) else 0
                        except (KeyError, TypeError, ValueError, IndexError):
                            continue
                        if lower <= msc < upper and math.isfinite(bid) and math.isfinite(ask):
                            ticks[(msc, bid, ask)] = (msc, bid, ask, flags)
                            kept += 1
                    if kept == 0 and fx_session_open(start) and fx_session_open(end - timedelta(minutes=1)):
                        gaps.append((start, end, "BROKER_SERVER_EMPTY"))
                    if not ticks:
                        continue
                    sorted_keys = sorted(ticks)
                    hour_index[hour] = {"start_row": count,
                                        "end_row": count + len(sorted_keys),
                                        "first_ms": sorted_keys[0][0],
                                        "last_ms": sorted_keys[-1][0]}
                    if first_ms is None:
                        first_ms = sorted_keys[0][0]
                    last_ms = sorted_keys[-1][0]
                    for key in sorted_keys:
                        msc, bid, ask, flags = ticks[key]
                        writer.writerow((msc, repr(bid), repr(ask), flags))
                        if buffer.tell() >= 65536:
                            flush(archive)
                    count += len(sorted_keys)
                    del ticks
                flush(archive)
        if count:
            os.replace(temp, path)
            return count, first_ms, last_ms, digest.hexdigest(), gaps, hour_index
        return 0, None, None, None, gaps, hour_index
    finally:
        # Interrupted downloads never leave a partially valid-looking archive.
        temp.unlink(missing_ok=True)


def _names(row):
    dtype = getattr(row, "dtype", None)
    if dtype is not None and dtype.names:
        return dtype.names
    return row.keys() if hasattr(row, "keys") else ()


def _write_ticks(path: Path, ticks) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("time_msc", "bid", "ask", "flags"))
    for msc, bid, ask, flags in ticks:
        writer.writerow((msc, repr(bid), repr(ask), flags))
    raw = buffer.getvalue().encode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with open(temp, "wb") as handle:
        # No name and mtime=0 keep the archive byte-identical for identical ticks.
        with gzip.GzipFile(filename="", fileobj=handle, mode="wb", mtime=0) as archive:
            archive.write(raw)
    os.replace(temp, path)
    return hashlib.sha256(raw).hexdigest()


def read_ticks(path: Path):
    with gzip.open(path, "rt", encoding="ascii", newline="") as handle:
        reader = csv.reader(handle)
        next(reader)
        return [(int(m), float(b), float(a), int(f)) for m, b, a, f in reader]


def reconcile(db, symbol: str, day: str, ticks, tick_size) -> tuple[int, int]:
    """Compare each observer snapshot of the day with the latest stored tick at or before it."""
    times = [tick[0] for tick in ticks]
    tolerance = (float(tick_size) if _finite(tick_size) and float(tick_size) > 0 else 0.0) * 1.000001
    checked = matched = 0
    for epoch, bid, ask in db.execute(
            "SELECT tick_epoch, bid, ask FROM observer_quotes WHERE symbol=? AND status='OK' "
            "AND substr(observed_utc,1,10)=?", (symbol, day)):
        checked += 1
        msc = int(round(epoch * 1000))
        index = bisect_right(times, msc) - 1
        # Several ticks may share one millisecond; any of them may be the one the observer read.
        while index >= 0:
            _, tick_bid, tick_ask, _ = ticks[index]
            if abs(tick_bid - bid) <= tolerance and abs(tick_ask - ask) <= tolerance:
                matched += 1
                break
            if index == 0 or times[index - 1] != times[index] or times[index] != msc:
                break
            index -= 1
    return checked, matched


def _match_hour_ticks(ticks, snapshots, tick_size) -> int:
    """Match each snapshot against the latest eligible ms, including duplicates."""
    tolerance = (float(tick_size) if _finite(tick_size) and float(tick_size) > 0 else 0.0) * 1.000001
    times = [r[0] for r in ticks]
    matched = 0
    for msc, bid, ask in snapshots:
        index = bisect_right(times, msc) - 1
        while index >= 0:
            _, tick_bid, tick_ask, _ = ticks[index]
            if abs(tick_bid - bid) <= tolerance and abs(tick_ask - ask) <= tolerance:
                matched += 1
                break
            if index == 0 or times[index - 1] != times[index] or times[index] != msc:
                break
            index -= 1
    return matched


def _reconcile_archive(db, symbol: str, day: str, path: Path, hour_index, tick_size):
    """Reconcile snapshots while decoding only relevant hours into memory."""
    snapshots = db.execute(
        "SELECT tick_epoch, bid, ask FROM observer_quotes WHERE symbol=? AND status='OK' "
        "AND substr(observed_utc,1,10)=?", (symbol, day)).fetchall()
    grouped = {}
    available = sorted(hour_index)
    for epoch, bid, ask in snapshots:
        msc = int(round(epoch * 1000))
        eligible = [hour for hour in available if hour_index[hour]["first_ms"] <= msc]
        if eligible:
            grouped.setdefault(eligible[-1], []).append((msc, bid, ask))
    if not grouped:
        return len(snapshots), 0

    # gzip has no random-access seek guarantee: scan rows once, but only parse
    # hours containing snapshots, never build an all-day list of ticks.
    ordered = sorted(grouped)
    pending = iter(ordered)
    current = next(pending, None)
    hour_ticks = []
    matched = 0
    with gzip.open(path, "rt", encoding="ascii", newline="") as stream:
        reader = csv.reader(stream)
        next(reader)
        for row_no, row in enumerate(reader):
            if current is None:
                break
            while current is not None and row_no >= hour_index[current]["end_row"]:
                matched += _match_hour_ticks(hour_ticks, grouped[current], tick_size)
                hour_ticks = []
                current = next(pending, None)
            if current is not None and row_no >= hour_index[current]["start_row"]:
                msc, bid, ask, flags = row
                hour_ticks.append((int(msc), float(bid), float(ask), int(flags)))
    if current is not None:
        matched += _match_hour_ticks(hour_ticks, grouped[current], tick_size)
    return len(snapshots), matched


def collect_tick_days(db, mt5, root, now: datetime, *, budget: int = 1) -> dict:
    """Download at most ``budget`` completed, observed symbol-days of broker ticks."""
    setup(db)
    now = _utc(now)
    if type(budget) is not int or not 1 <= budget <= 7:
        raise ValueError("tick_budget_1_to_7")
    done = []
    for symbol, day in _due_days(db, now)[:budget]:
        day_start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        previous = db.execute("SELECT attempts FROM broker_tick_days WHERE symbol=? AND day=?",
                              (symbol, day)).fetchone()
        attempts = (previous[0] if previous else 0) + 1
        info = mt5.symbol_info(symbol)
        tick_size = _finite(getattr(info, "trade_tick_size", None)) or _finite(getattr(info, "point", None))
        path = tick_path(root, symbol, day)
        count, first_ms, last_ms, digest, gaps, hour_index = _download_day(
            mt5, symbol, day_start, path)
        whole_day_missing = not count and any(reason == "BROKER_HISTORY_UNAVAILABLE" for *_, reason in gaps)
        with db:
            if whole_day_missing and attempts < TICK_MAX_ATTEMPTS:
                db.execute("INSERT INTO broker_tick_days(symbol, day, status, attempts, next_epoch, reason) "
                           "VALUES(?,?,?,?,?,?) ON CONFLICT(symbol, day) DO UPDATE SET status=excluded.status, "
                           "attempts=excluded.attempts, next_epoch=excluded.next_epoch, reason=excluded.reason",
                           (symbol, day, "RETRY", attempts, now.timestamp() + TICK_RETRY_SECONDS,
                            "BROKER_HISTORY_UNAVAILABLE"))
                done.append({"symbol": symbol, "day": day, "status": "RETRY", "attempts": attempts})
                continue
            if not count:
                _record_gap(db, "broker_ticks", symbol, day_start, day_start + timedelta(days=1),
                            "NO_BROKER_TICKS_FOR_OBSERVED_DAY", now)
                status, digest, file_name = "GAP", None, None
                checked = matched = 0
            else:
                file_name = path.relative_to(Path(root)).as_posix()
                for start, end, reason in gaps:
                    _record_gap(db, "broker_ticks", symbol, start, end, reason, now)
                status = "STORED_WITH_GAPS" if gaps else "STORED"
                checked, matched = _reconcile_archive(db, symbol, day, path, hour_index, tick_size)
            db.execute(
                "INSERT INTO broker_tick_days(symbol, day, status, attempts, next_epoch, ticks, first_epoch, "
                "last_epoch, sha256, file, collected_utc, reason, snapshots_checked, snapshots_matched, tick_size) "
                "VALUES(?,?,?,?,0,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(symbol, day) DO UPDATE SET "
                "status=excluded.status, attempts=excluded.attempts, next_epoch=0, ticks=excluded.ticks, "
                "first_epoch=excluded.first_epoch, last_epoch=excluded.last_epoch, sha256=excluded.sha256, "
                "file=excluded.file, collected_utc=excluded.collected_utc, reason=excluded.reason, "
                "snapshots_checked=excluded.snapshots_checked, snapshots_matched=excluded.snapshots_matched, "
                "tick_size=excluded.tick_size",
                (symbol, day, status, attempts, count,
                 first_ms / 1000 if count else None, last_ms / 1000 if count else None,
                 digest, file_name, now.isoformat(), None if status == "STORED" else "GAPS_RECORDED",
                 checked, matched, tick_size))
        done.append({"symbol": symbol, "day": day, "status": status, "ticks": count,
                     "gaps": len(gaps), "snapshots_checked": checked, "snapshots_matched": matched})
    return {"schema_version": SCHEMA_VERSION, "collected": done,
            "pending_days": len(_due_days(db, now)), "orders_submitted": 0}
