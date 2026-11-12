"""Convert the read-only MT5 session probe CSV to a D9 *candidate* schedule.

Safety: Never certifies a broker day, UTC/DST, or a historical validity interval.
The output deliberately retains null validity and empty verified_broker_dates,
so BrokerSessions.classify() cannot treat these rows as authenticated CLOSED.
Run on an approved research machine, not the production VPS.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys

FIELDS = (
    "record_type", "broker_server", "captured_host_utc", "broker_wall_time",
    "symbol", "weekday_mon0", "kind", "session_index", "from_seconds",
    "to_seconds", "status", "error_code",
)
KINDS = ("quote", "trade")


def build_candidate(raw: bytes, required_symbols: list[str]) -> dict:
    """Fail closed on missing, ambiguous, duplicate, or malformed probe rows."""
    if not raw or len(raw) > 2_000_000:
        raise ValueError("D9_CAPTURE_SIZE_INVALID")
    if not required_symbols or len(set(required_symbols)) != len(required_symbols):
        raise ValueError("D9_UNIVERSE_INVALID")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), delimiter=";")
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("D9_CAPTURE_HEADER_INVALID")
        rows = list(reader)
    except UnicodeDecodeError as exc:
        raise ValueError("D9_CAPTURE_ENCODING_INVALID") from exc
    if not rows or len(rows) > 20_000 or any(None in row for row in rows):
        raise ValueError("D9_CAPTURE_ROWS_INVALID")
    meta = [row for row in rows if row["record_type"] == "META"]
    if len(meta) != 1:
        raise ValueError("D9_CAPTURE_META_INVALID")
    meta = meta[0]
    if meta["status"] != "HOST_CLOCK_UNVERIFIED" or not meta["broker_server"].strip():
        raise ValueError("D9_CAPTURE_BROKER_INVALID")
    try:
        # TimeGMT() comes from terminal/host settings. This timestamp is NOT an
        # independent UTC proof, and validity below intentionally stays null.
        captured = datetime.strptime(meta["captured_host_utc"], "%Y.%m.%d %H:%M:%S")
        captured = captured.replace(tzinfo=timezone.utc).isoformat()
    except ValueError as exc:
        raise ValueError("D9_CAPTURE_TIME_INVALID") from exc
    if not meta["broker_wall_time"]:
        raise ValueError("D9_CAPTURE_TIME_MISSING")
    universe = set(required_symbols)
    records: dict[tuple[str, int, str], dict[str, object]] = {}
    for row in rows:
        typ = row["record_type"]
        if typ == "META":
            continue
        if typ not in ("SESSION", "NO_SESSION_OR_UNAVAILABLE"):
            raise ValueError("D9_CAPTURE_INCOMPLETE_OR_ERROR")
        if (row["broker_server"] != meta["broker_server"]
                or row["captured_host_utc"] != meta["captured_host_utc"]
                or row["broker_wall_time"] != meta["broker_wall_time"]):
            raise ValueError("D9_CAPTURE_MIXED_SNAPSHOT")
        symbol = row["symbol"]
        if symbol not in universe or row["kind"] not in KINDS:
            raise ValueError("D9_CAPTURE_SYMBOL_INVALID")
        try:
            weekday = int(row["weekday_mon0"])
            index = int(row["session_index"])
        except ValueError as exc:
            raise ValueError("D9_CAPTURE_INDEX_INVALID") from exc
        if not 0 <= weekday <= 6 or not 0 <= index < 32:
            raise ValueError("D9_CAPTURE_INDEX_INVALID")
        key = (symbol, weekday, row["kind"])
        item = records.setdefault(key, {"unavailable": False, "indices": {}})
        indices = item["indices"]
        if typ == "NO_SESSION_OR_UNAVAILABLE":
            if row["status"] != "UNVERIFIED" or index != 0 or item["unavailable"] or indices:
                raise ValueError("D9_CAPTURE_AMBIGUOUS")
            item["unavailable"] = True
        else:
            if row["status"] != "REPORTED" or item["unavailable"] or index in indices:
                raise ValueError("D9_CAPTURE_DUPLICATE")
            try:
                start = int(row["from_seconds"])
                end = int(row["to_seconds"])
            except ValueError as exc:
                raise ValueError("D9_CAPTURE_INTERVAL_INVALID") from exc
            if not (0 <= start < 86400 and start < end <= 172800):
                raise ValueError("D9_CAPTURE_INTERVAL_INVALID")
            indices[index] = [start, end]

    expected = {(symbol, day, kind) for symbol in required_symbols
                for day in range(7) for kind in KINDS}
    if set(records) != expected:
        raise ValueError("D9_CAPTURE_UNIVERSE_INCOMPLETE")
    symbols: dict[str, dict] = {}
    for symbol in required_symbols:
        symbols[symbol] = {kind: {} for kind in KINDS}
        for kind in KINDS:
            for day in range(7):
                item = records[(symbol, day, kind)]
                indices = item["indices"]
                if item["unavailable"]:
                    sessions = None  # Unknown; never infer a closed market.
                else:
                    if not indices or sorted(indices) != list(range(len(indices))):
                        raise ValueError("D9_CAPTURE_NONCONTIGUOUS_SESSIONS")
                    sessions = [indices[index] for index in range(len(indices))]
                    if any(a[1] > b[0] for a, b in zip(sessions, sessions[1:])):
                        raise ValueError("D9_CAPTURE_OVERLAPPING_SESSIONS")
                symbols[symbol][kind][str(day)] = sessions
    return {
        "schema_version": 1,
        "description": (
            "PROBE CANDIDATE ONLY: weekly server-wall-clock sessions, NOT a "
            "certified historical/holiday schedule. Host UTC unverified. "
            "Null weekdays mean NO_SESSION_OR_UNAVAILABLE, not CLOSED."
        ),
        "broker_server_sha256": hashlib.sha256(
            meta["broker_server"].encode("utf-8")).hexdigest(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "captured_at_utc": captured,
        "valid_from_utc": None,
        "valid_until_utc": None,
        "verified_broker_dates": [],
        "symbols": symbols,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--universe", type=Path, default=(
        Path(__file__).resolve().parents[2] / "config" / "observer_universe.json"))
    args = parser.parse_args(argv)
    try:
        raw = args.csv.read_bytes()
        required = json.loads(args.universe.read_text(encoding="utf-8"))["core"]
        result = build_candidate(raw, required)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print("D9_CAPTURE_BLOCKED", str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print("D9_CAPTURE_DIAGNOSTIC_ONLY: schedule NOT certified; never activate as policy",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
