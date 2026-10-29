"""Development-context export with verified lineage (docs/ROADMAP.md, Tahap 2 input from Tahap 0 data).

Builds :class:`katarina.research.market_intelligence.MarketContext` rows for candidate signals from the
broker tick files collected by the Stage 0 ledger. Read-only: the ledger database is opened by the
caller in read-only mode and tick files are only read.

Lineage rules:

* Only tick days the ledger recorded as ``STORED`` or ``STORED_WITH_GAPS`` are used, and each file's
  SHA-256 (of the decompressed CSV, as written by the ledger) must equal the recorded hash.
* Only ticks strictly before the entry are used; ``observed_at`` is the last such tick. Range and ATR
  come from complete (closed) bars only; ``tick_count`` counts every tick in the window.
* A window that overlaps a recorded broker-tick gap, a split GAP, or leaves the development period
  gets **no** context, and the reason is recorded. Nothing is interpolated or backfilled.
* ``source_sha256`` binds each context to the exact tick files and export parameters used.

Missing contexts are reported, never invented; Stage 2 then WAITs them as ``WAIT_MISSING_CONTEXT``.
No broker access, no orders, no live authority.
"""
from __future__ import annotations

from bisect import bisect_left
import gzip
import hashlib
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.research import validation as v
from katarina.research.market_intelligence import MarketContext

USABLE_TICK_DAY_STATUSES = ("STORED", "STORED_WITH_GAPS")


def iter_verified_ticks(root: Path, record: dict):
    """Yield (time_msc, bid, ask) from one ledger tick file after verifying its recorded hash.

    Two-pass streaming:
    Pass 1: verify sha256 hash of decompressed content.
    Pass 2: yield (time_msc, bid, ask) for valid tick lines.
    """
    file_path = Path(root) / record["file"]

    # Pass 1: SHA256 of decompressed CSV content
    hasher = hashlib.sha256()
    with gzip.open(file_path, "rb") as gz:
        while chunk := gz.read(65536):
            hasher.update(chunk)
    if hasher.hexdigest() != record["sha256"]:
        raise v.ValidationError("TICK_FILE_HASH_MISMATCH")

    # Pass 2: same strict 4-column contract as the archive writer (time_msc,bid,ask,flags).
    with gzip.open(file_path, "rt", encoding="ascii", newline="") as gz:
        next(gz, None)  # Skip CSV header line
        for line in gz:
            try:
                msc, bid, ask, _ = line.rstrip("\n").split(",")
                msc, bid_f, ask_f = int(msc), float(bid), float(ask)
            except ValueError as error:
                raise v.ValidationError("TICK_FILE_MALFORMED") from error
            if math.isfinite(bid_f) and math.isfinite(ask_f) and bid_f > 0 and ask_f >= bid_f:
                yield msc, bid_f, ask_f


def _ticks(root: Path, record) -> list[tuple[int, float]]:
    """(time_msc, mid) from one ledger tick file after verifying its recorded hash."""
    return [(msc, (bid + ask) / 2) for msc, bid, ask in iter_verified_ticks(root, record)]


def _closed_bars(ticks, start: datetime, end: datetime, bar_minutes: int, atr_bars: int):
    """(range, atr) from complete bars inside [start, end); None when there are too few.

    Range is max high - min low over every complete bar with ticks. ATR is the mean true range of
    the last ``atr_bars`` bars of the trailing run of consecutive non-empty bars: a bar without ticks
    breaks the series rather than being filled.
    """
    width = bar_minutes * 60_000
    begin = int(start.timestamp() * 1000)
    first = -(-begin // width) * width  # first bar boundary at or after start
    last_end = int(end.timestamp() * 1000) // width * width
    highs, lows, trs, previous_close = [], [], [], None
    for bar_start in range(first, last_end, width):
        lo, hi = bisect_left(ticks, (bar_start,)), bisect_left(ticks, (bar_start + width,))
        prices = [mid for _, mid in ticks[lo:hi]]
        if not prices:
            trs, previous_close = [], None
            continue
        high, low = max(prices), min(prices)
        highs.append(high)
        lows.append(low)
        trs.append(high - low if previous_close is None else
                   max(high - low, abs(high - previous_close), abs(low - previous_close)))
        previous_close = prices[-1]
    if len(trs) < atr_bars:
        return None, None
    return max(highs) - min(lows), sum(trs[-atr_bars:]) / atr_bars


def export_contexts(db, root, signals, *, symbol: str, split: v.DataSplit, lookback_minutes: int,
                    bar_minutes: int, atr_bars: int) -> tuple[list[dict], dict]:
    """Return (context rows, manifest). ``signals`` are :class:`~katarina.research.validation.Trade`."""
    for name, value in (("lookback_minutes", lookback_minutes), ("bar_minutes", bar_minutes),
                        ("atr_bars", atr_bars)):
        if type(value) is not int or value < 1:
            raise v.ValidationError(f"{name}_must_be_positive_int")
    if bar_minutes * atr_bars > lookback_minutes:
        raise v.ValidationError("lookback_shorter_than_atr_bars")
    if not isinstance(symbol, str) or not symbol.strip():
        raise v.ValidationError("symbol_required")
    root = Path(root)
    parameters = {"symbol": symbol, "lookback_minutes": lookback_minutes, "bar_minutes": bar_minutes,
                  "atr_bars": atr_bars, "split_sha256": split.sha256}
    if "server_shift_hours" not in {row[1] for row in db.execute("PRAGMA table_info(broker_tick_days)")}:
        raise v.ValidationError("TICK_CLOCK_BASIS_UNKNOWN")
    days = {row[0]: {"status": row[1], "sha256": row[2], "file": row[3],
                     "server_shift_hours": row[4]} for row in db.execute(
        "SELECT day, status, sha256, file, server_shift_hours FROM broker_tick_days WHERE symbol=?",
        (symbol,))}
    gaps = [(v._utc(s), v._utc(e), r) for s, e, r in db.execute(
        "SELECT start_utc, end_utc, reason FROM data_gaps WHERE stream='broker_ticks' AND symbol=?", (symbol,))]
    cache, rows, missing, sources = {}, [], [], set()
    for trade in sorted(signals, key=lambda t: (t.entry_at, t.trade_id)):
        entry = v._utc(trade.entry_at)
        start = entry - timedelta(minutes=lookback_minutes)
        reason = None
        if split.period(start) != "DEVELOPMENT" or split.period(entry) != "DEVELOPMENT" or any(
                start < e and entry > s for s, e, _ in split.gaps):
            reason = "WINDOW_OUTSIDE_DEVELOPMENT_OR_IN_GAP"
        elif any(start < e and entry > s for s, e, _ in gaps):
            reason = "BROKER_TICK_GAP_IN_WINDOW"
        ticks, used = [], []
        day = start.date()
        while reason is None and day <= entry.date():
            key = day.isoformat()
            record = days.get(key)
            if record is not None and record["server_shift_hours"] is None:
                reason = "TICK_CLOCK_BASIS_UNKNOWN"
                break
            if record is None or record["status"] not in USABLE_TICK_DAY_STATUSES or not record["file"]:
                reason = "TICK_DAY_NOT_STORED"
                break
            if key not in cache:
                try:
                    cache[key] = _ticks(root, record)
                except (OSError, ValueError, EOFError) as error:
                    cache[key] = str(error) if isinstance(error, v.ValidationError) else "TICK_FILE_UNREADABLE"
            if isinstance(cache[key], str):
                reason = cache[key]
                break
            ticks.extend(cache[key])
            used.append((key, record["sha256"]))
            day += timedelta(days=1)
        if reason is None:
            lo = bisect_left(ticks, (int(start.timestamp() * 1000),))
            hi = bisect_left(ticks, (int(entry.timestamp() * 1000),))  # strictly before entry
            window = ticks[lo:hi]
            price_range, atr = _closed_bars(window, start, entry, bar_minutes, atr_bars)
            if len(window) < 2:
                reason = "TOO_FEW_TICKS"
            elif atr is None:
                reason = "INSUFFICIENT_COMPLETE_BARS"
            elif price_range <= 0 or atr <= 0:
                reason = "ZERO_RANGE"
        if reason:
            missing.append({"trade_id": trade.trade_id, "reason": reason})
            continue
        observed = datetime.fromtimestamp(window[-1][0] / 1000, timezone.utc)
        source = v.sha256_text(v.canonical({"parameters": parameters, "tick_days": used}))
        context = MarketContext(trade_id=trade.trade_id, symbol=symbol, window_start=start, observed_at=observed,
                                range_price=price_range, atr_price=atr, tick_count=len(window),
                                source_sha256=source)
        sources.update(used)
        rows.append({"trade_id": context.trade_id, "symbol": context.symbol,
                     "window_start": context.window_start.isoformat(), "observed_at": context.observed_at.isoformat(),
                     "range_price": context.range_price, "atr_price": context.atr_price,
                     "tick_count": context.tick_count, "source_sha256": context.source_sha256})
    reasons = {}
    for item in missing:
        reasons[item["reason"]] = reasons.get(item["reason"], 0) + 1
    manifest = {"schema_version": 1, "tool": "katarina.research.context_export", "parameters": parameters,
                "signals": len(rows) + len(missing), "contexts": len(rows), "missing": missing,
                "missing_reasons": dict(sorted(reasons.items())),
                "tick_sources": [{"day": d, "sha256": h} for d, h in sorted(sources)],
                "contexts_sha256": v.sha256_text(v.canonical(rows)), "live_execution_authorized": False,
                "note": "Contexts come only from hash-verified Stage 0 broker tick files; missing windows are "
                        "reported, never filled. Tick count is activity, not order-book liquidity."}
    manifest["manifest_sha256"] = v.sha256_text(v.canonical(manifest))
    return rows, manifest
