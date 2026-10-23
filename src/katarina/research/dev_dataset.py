"""WP8a development-only broker bars: frozen hash lineage and holdout firewall.

Tahap 1–2, preparing Tahap 4. Read-only broker inputs, research files only;
nothing here sends orders, trains on holdout or promotes a strategy.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.research.validation import ValidationError, _utc, canonical, sha256_text

DEV_CUTOFF_UTC = datetime(2026, 10, 13, tzinfo=timezone.utc)
TIMEFRAMES = {"M5": 5, "M15": 15, "H1": 60, "H4": 240}
CSV_FIELDS = ("time_utc", "open", "high", "low", "close",
              "tick_volume", "spread", "real_volume", "closed_at_utc")
_VALID_SYMBOL = re.compile(r"^[A-Za-z0-9_.#-]{1,40}$")


def _range(start, end):
    start, end = _utc(start), _utc(end)
    if end > DEV_CUTOFF_UTC or start >= DEV_CUTOFF_UTC:
        raise ValidationError("holdout_data_forbidden")
    if start >= end:
        raise ValidationError("development_range_invalid")
    return start, end


def _symbols(core):
    if (not isinstance(core, (list, tuple)) or not core
            or any(type(s) is not str or not _VALID_SYMBOL.fullmatch(s) for s in core)
            or len(set(core)) != len(core) or len(core) > 17):
        raise ValidationError("development_symbols_invalid")
    return tuple(core)


def _metadata(broker, symbol):
    info = broker.symbol_info(symbol)
    if info is None:
        raise ValidationError("broker_symbol_metadata_unavailable")
    fields = ("point", "trade_tick_size", "trade_contract_size")
    try:
        values = tuple(float(getattr(info, key)) for key in fields)
    except (TypeError, ValueError, AttributeError) as error:
        raise ValidationError("broker_symbol_metadata_invalid") from error
    if not all(math.isfinite(x) and x > 0 for x in values):
        raise ValidationError("broker_symbol_metadata_invalid")
    return dict(zip(fields, values))


def _row(rate, minutes, start, end):
    try:
        epoch = int(rate["time"])
        opened = datetime.fromtimestamp(epoch, timezone.utc)
    except (KeyError, ValueError, TypeError, OverflowError, OSError) as error:
        raise ValidationError("development_bar_time_invalid") from error
    if opened >= DEV_CUTOFF_UTC:
        raise ValidationError("holdout_data_forbidden")
    if opened < start or opened >= end:
        return None
    closed = opened + timedelta(minutes=minutes)
    if closed > DEV_CUTOFF_UTC or closed > end:
        raise ValidationError("development_bar_not_closed")
    if epoch % (minutes * 60):
        raise ValidationError("development_bar_time_unaligned")
    try:
        prices = tuple(float(rate[name]) for name in ("open", "high", "low", "close"))
        volume = int(rate["tick_volume"])
        spread = int(rate["spread"])
        real_volume = int(rate["real_volume"])
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ValidationError("development_bar_values_invalid") from error
    op, hi, lo, cl = prices
    if (not all(math.isfinite(x) and x > 0 for x in prices)
            or lo > min(op, cl) or hi < max(op, cl) or hi < lo
            or min(volume, spread, real_volume) < 0):
        raise ValidationError("development_bar_values_invalid")
    return (opened.isoformat(), *(repr(x) for x in prices),
            volume, spread, real_volume, closed.isoformat())


def _bar_stream(broker, symbol, timeframe, start, end, chunk_days):
    minutes = TIMEFRAMES[timeframe]
    frame = getattr(broker, "TIMEFRAME_" + timeframe, timeframe)
    cursor = start
    previous = None
    missing_until = start
    while cursor < end:
        upper = min(cursor + timedelta(days=chunk_days), end)
        # MT5 range can include the end tick; remove it in the range query,
        # and independently refuse any holdout bar returned by the broker.
        rows = broker.copy_rates_range(
            symbol, frame, cursor, upper - timedelta(microseconds=1))
        if rows is None:
            yield None, (cursor.isoformat(), upper.isoformat(), "BROKER_HISTORY_UNAVAILABLE")
            missing_until = upper
        elif len(rows) == 0:
            yield None, (cursor.isoformat(), upper.isoformat(), "BROKER_SERVER_EMPTY")
            missing_until = upper
        else:
            if len(rows) > 50000:
                raise ValidationError("DEVELOPMENT_CHUNK_OVER_LIMIT")
            dedup = {}
            for raw in rows:
                row = _row(raw, minutes, start, end)
                if row is None:
                    continue
                key = row[0]
                if key in dedup and dedup[key] != row:
                    raise ValidationError("DEVELOPMENT_CONFLICTING_BAR")
                dedup[key] = row
            for key in sorted(dedup):
                row = dedup[key]
                opened = datetime.fromisoformat(row[0])
                if previous is None and opened > missing_until:
                    yield None, (missing_until.isoformat(), opened.isoformat(), "BROKER_BAR_GAP")
                if previous is not None:
                    if opened <= previous:
                        if opened == previous:
                            continue
                        raise ValidationError("DEVELOPMENT_BARS_NOT_MONOTONIC")
                    gap_start = previous + timedelta(minutes=minutes)
                    gap_start = max(gap_start, missing_until)
                    if opened > gap_start:
                        yield None, (gap_start.isoformat(), opened.isoformat(), "BROKER_BAR_GAP")
                previous = opened
                yield row, None
        cursor = upper
    if previous is not None:
        tail = max(previous + timedelta(minutes=minutes), missing_until)
        if tail < end:
            yield None, (tail.isoformat(), end.isoformat(), "BROKER_BAR_GAP")


def _archive(broker, symbol, timeframe, start, end, root, chunk_days, metadata):
    path = root / symbol / (timeframe + ".csv.gz")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    count, first, last, gaps = 0, None, None, []
    try:
        with temp.open("wb") as raw:
            with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipfile:
                with io.TextIOWrapper(zipfile, encoding="ascii", newline="") as text:
                    writer = csv.writer(text, lineterminator="\n")
                    writer.writerow(CSV_FIELDS)
                    for row, gap in _bar_stream(broker, symbol, timeframe,
                                                start, end, chunk_days):
                        if gap:
                            gaps.append(dict(start_utc=gap[0], end_utc=gap[1],
                                             reason=gap[2]))
                        if row:
                            writer.writerow(row)
                            count += 1
                            first = first or row[0]
                            last = row[0]
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    return dict(symbol=symbol, timeframe=timeframe, bars=count,
                first_utc=first, last_utc=last, gaps=gaps,
                sha256=digest, bytes=path.stat().st_size, **metadata)


def export_dev_bars(broker, core, *, start, out, end=DEV_CUTOFF_UTC,
                    chunk_days: int = 7) -> dict:
    """Export closed development bars; source is injected and read-only.

    Each interval is bounded; missing periods are recorded and never filled.
    Actual VPS invocation belongs to Claude, not the observer worker.
    """
    start, end = _range(start, end)
    symbols = _symbols(core)
    if type(chunk_days) is not int or not 1 <= chunk_days <= 7:
        raise ValidationError("development_chunk_days_invalid")
    root = Path(out)
    if root.is_symlink() or (root / "manifest.json").exists():
        raise ValidationError("development_dataset_already_frozen")
    files = {}
    for symbol in symbols:
        metadata = _metadata(broker, symbol)
        for timeframe in TIMEFRAMES:
            key = symbol + "/" + timeframe + ".csv.gz"
            files[key] = _archive(broker, symbol, timeframe,
                                  start, end, root, chunk_days, metadata)
    manifest = {"schema_version": 1, "stage": "WP8A_DEVELOPMENT_ONLY",
                "development_start": start.isoformat(),
                "development_end": end.isoformat(),
                "cutoff_utc": DEV_CUTOFF_UTC.isoformat(),
                "symbols": list(symbols), "files": files,
                "live_execution_authorized": False}
    manifest["manifest_sha256"] = sha256_text(canonical(manifest))
    tmp = root / "manifest.tmp"
    try:
        tmp.write_text(canonical(manifest) + "\n", encoding="utf-8", newline="\n")
        os.replace(tmp, root / "manifest.json")
    finally:
        tmp.unlink(missing_ok=True)
    return manifest


def _read_archive(path, record, start, end):
    if not path.is_file() or path.is_symlink():
        raise ValidationError("development_file_missing")
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if (path.stat().st_size != record["bytes"] or digest != record["sha256"]):
        raise ValidationError("development_file_hash_mismatch")
    try:
        with gzip.open(path, "rt", encoding="ascii", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != CSV_FIELDS:
                raise ValidationError("development_csv_header_invalid")
            rows = []
            for item in reader:
                opened = _utc(item["time_utc"])
                closed = _utc(item["closed_at_utc"])
                if opened >= DEV_CUTOFF_UTC or closed > DEV_CUTOFF_UTC:
                    raise ValidationError("holdout_data_forbidden")
                if not start <= opened < end:
                    raise ValidationError("development_bar_outside_export_range")
                if opened + timedelta(minutes=TIMEFRAMES[record["timeframe"]]) != closed:
                    raise ValidationError("development_bar_close_invalid")
                original = {"time": int(opened.timestamp()), **{
                    col: float(item[col]) for col in ("open", "high", "low", "close")},
                    **{col: int(item[col]) for col in ("tick_volume", "spread", "real_volume")}}
                if _row(original, TIMEFRAMES[record["timeframe"]], start, end) is None:
                    raise ValidationError("development_bar_outside_export_range")
                if rows and opened <= _utc(rows[-1]["time_utc"]):
                    raise ValidationError("DEVELOPMENT_BARS_NOT_MONOTONIC")
                rows.append({**item, "open": original["open"],
                             "high": original["high"], "low": original["low"],
                             "close": original["close"], "tick_volume": original["tick_volume"],
                             "spread": original["spread"], "real_volume": original["real_volume"]})
    except (OSError, EOFError, UnicodeError, csv.Error, KeyError, ValueError) as error:
        if isinstance(error, ValidationError):
            raise
        raise ValidationError("development_csv_invalid") from error
    if (len(rows) != record["bars"]
            or (rows[0]["time_utc"] if rows else None) != record["first_utc"]
            or (rows[-1]["time_utc"] if rows else None) != record["last_utc"]):
        raise ValidationError("development_file_row_count_mismatch")
    return rows


def load_dev_dataset(path):
    """Offline verified development bars by symbol/timeframe; no MT5 or network."""
    root = Path(path)
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ValidationError("development_manifest_unreadable") from error
    digest = manifest.get("manifest_sha256")
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if sha256_text(canonical(body)) != digest:
        raise ValidationError("development_manifest_hash_mismatch")
    if manifest.get("cutoff_utc") != DEV_CUTOFF_UTC.isoformat():
        raise ValidationError("holdout_data_forbidden")
    start, end = _range(manifest["development_start"], manifest["development_end"])
    symbols = _symbols(manifest["symbols"])
    expected = {symbol + "/" + tf + ".csv.gz" for symbol in symbols for tf in TIMEFRAMES}
    if set(manifest["files"]) != expected:
        raise ValidationError("development_manifest_files_invalid")
    output = {}
    for symbol in symbols:
        output[symbol] = {}
        for timeframe in TIMEFRAMES:
            key = symbol + "/" + timeframe + ".csv.gz"
            record = manifest["files"][key]
            if record["symbol"] != symbol or record["timeframe"] != timeframe:
                raise ValidationError("development_manifest_metadata_invalid")
            output[symbol][timeframe] = _read_archive(root / key, record, start, end)
    return output
