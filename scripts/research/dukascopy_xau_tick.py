#!/usr/bin/env python3
"""Bounded XAUUSD Dukascopy tick acquisition, UTC, offline research only.

No MT5, broker login, Stage0 state or orders. Source: Dukascopy hourly .bi5
LZMA; preserve original hourly bytes/hash and millisecond source ordering.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
import lzma
import math
from pathlib import Path
import struct
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://datafeed.dukascopy.com/datafeed/XAUUSD"
RECORD = struct.Struct(">IIIff")
SCALE = 1000
DEV_CUTOFF = date(2026, 10, 13)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def extract_ticks(payload: bytes, day: date, hour: int):
    data = lzma.decompress(payload)
    if len(data) % RECORD.size:
        raise ValueError("TRUNCATED_BI5_RECORD")
    anchor = int(datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc).timestamp() * 1000)
    prev = -1
    for ms, ask_i, bid_i, avol, bvol in RECORD.iter_unpack(data):
        if not 0 <= ms < 3_600_000 or ms < prev:
            raise ValueError("UNORDERED_TICK_TIME")
        if not (math.isfinite(avol) and math.isfinite(bvol) and avol >= 0 and bvol >= 0):
            raise ValueError("INVALID_PROVIDER_VOLUME")
        if not 100_000 <= bid_i <= ask_i <= 20_000_000:
            raise ValueError("INVALID_XAU_QUOTE_OR_SCALE")
        prev = ms
        yield anchor + ms, f"{bid_i / SCALE:.3f}", f"{ask_i / SCALE:.3f}"


def fetch_hour(url: str, tries: int = 2) -> tuple[bytes | None, str]:
    for attempt in range(tries):
        try:
            req = Request(url, headers={"User-Agent": "Katarina-Research-Historical-Ticks/1.0"})
            with urlopen(req, timeout=18) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP_{response.status}")
                return response.read(18 * 1024 * 1024 + 1), "HTTP_200"
        except HTTPError as error:
            if error.code == 404:
                return None, "HTTP_404_NO_FILE"
            reason = f"HTTP_{error.code}"
        except (URLError, TimeoutError, OSError, RuntimeError) as error:
            reason = f"NETWORK_ERROR:{type(error).__name__}"
        if attempt + 1 < tries:
            time.sleep(2 + 2 * attempt)
    return None, reason


def acquire_day(day: date, root: Path, delay: float, max_hours: int) -> dict:
    folder = root / day.isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    raw_dir = folder / "raw"
    raw_dir.mkdir(exist_ok=True)
    day_csv = folder / "ticks.csv.gz"
    temp_csv = folder / "ticks.csv.gz.part"
    hours = []
    total = 0
    failures = 0
    last_ms = -1
    with gzip.open(temp_csv, "wt", encoding="utf-8", newline="", compresslevel=6) as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("time_msc", "bid", "ask"))
        for hour in range(max_hours):
            url = f"{BASE}/{day.year}/{day.month - 1:02d}/{day.day:02d}/{hour:02d}h_ticks.bi5"
            payload, status = fetch_hour(url)
            note = {"hour_utc": hour, "url": url, "status": status, "rows": 0}
            if payload is None:
                if status != "HTTP_404_NO_FILE":
                    failures += 1
            elif len(payload) == 0:
                note["status"] = "HTTP_200_EMPTY"
            elif len(payload) > 18 * 1024 * 1024:
                note["status"] = "REJECTED_TOO_LARGE"
                failures += 1
            else:
                note["source_bytes"] = len(payload)
                note["source_sha256"] = digest(payload)
                try:
                    records = list(extract_ticks(payload, day, hour))
                    if records and records[0][0] < last_ms:
                        raise ValueError("OUT_OF_ORDER_BETWEEN_HOURS")
                    (raw_dir / f"{hour:02d}h_ticks.bi5").write_bytes(payload)
                    writer.writerows(records)
                    if records:
                        last_ms = records[-1][0]
                    note["rows"] = len(records)
                    note["status"] = "VALID_DECODED"
                    total += len(records)
                except (lzma.LZMAError, EOFError, ValueError) as error:
                    note["status"] = f"REJECTED:{type(error).__name__}:{str(error)[:100]}"
                    failures += 1
            hours.append(note)
            print(f"{day} {hour:02d}: {note['status']}, rows={note['rows']}", flush=True)
            if failures >= 3:
                print("STOP_AFTER_3_FAILED_HOURS", flush=True)
                break
            if delay:
                time.sleep(delay)
    temp_csv.replace(day_csv)
    manifest = {
        "provider": "Dukascopy (NOT Valetax)",
        "symbol": "XAUUSD",
        "date_utc": day.isoformat(),
        "price_divisor": SCALE,
        "time_zone": "UTC",
        "tick_csv_gz_sha256": digest(day_csv.read_bytes()),
        "tick_csv_gz_bytes": day_csv.stat().st_size,
        "tick_count": total,
        "hours_attempted": len(hours),
        "hours_expected": max_hours,
        "network_or_decode_failures": failures,
        "hours": hours,
        "research_role": "development_candidate" if day < DEV_CUTOFF else "holdout_not_for_tuning",
        "status": ("ACQUIRED_PENDING_SESSIONS_COST_AND_COVERAGE_VERIFICATION"
                   if total > 0 and failures == 0 and len(hours) == max_hours
                   else "INCOMPLETE_NOT_BACKTEST_READY"),
        "validation_limits": [
            "Provider session schedule not independently verified",
            "Broker-specific commission/swap/slippage not verified",
            "Quote completeness not certified",
            "Not a Valetax broker feed",
            "Not a production trading or promotion approval"],
        "orders_sent": 0,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def offline_selftest():
    day = date(2024, 1, 2)
    raw = RECORD.pack(1234, 2065123, 2065012, 0.3, 0.5)
    raw += RECORD.pack(1234, 2065223, 2065112, 0.1, 0.2)
    rows = list(extract_ticks(lzma.compress(raw, format=lzma.FORMAT_ALONE), day, 12))
    assert len(rows) == 2 and rows[0][1:] == ("2065.012", "2065.123")
    assert rows[0][0] == rows[1][0]
    print("OFFLINE_DECODE_SELFTEST_PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2024-01-02")
    parser.add_argument("--output", default="artifacts/xauusd-dukascopy")
    parser.add_argument("--delay", type=float, default=0.45)
    parser.add_argument("--max-hours", type=int, default=24)
    parser.add_argument("--selftest-only", action="store_true")
    args = parser.parse_args()
    offline_selftest()
    if args.selftest_only:
        return
    if not 1 <= args.max_hours <= 24 or not 0 <= args.delay <= 10:
        parser.error("invalid max hours / delay")
    day = date.fromisoformat(args.date)
    if not date(2024, 1, 1) <= day <= date(2026, 11, 13):
        parser.error("date outside requested scope")
    report = acquire_day(day, Path(args.output), args.delay, args.max_hours)
    print("FINAL_RESULT", json.dumps({
        k: report[k] for k in ("date_utc", "tick_count", "hours_attempted",
                             "network_or_decode_failures", "status", "orders_sent")}), flush=True)
    if report["status"] == "INCOMPLETE_NOT_BACKTEST_READY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
