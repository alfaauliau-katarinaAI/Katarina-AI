"""WP2 Tahap 0: streaming tick byte-identik, bounded memory; no orders.
Copy of the OLD serialization algorithm is intentionally kept in this test.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import math
import sqlite3
import tempfile
import tracemalloc
import unittest
from bisect import bisect_right
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from katarina.intelligence.operations import observation_ledger as ledger

DAY = datetime(2026, 10, 20, tzinfo=timezone.utc)


def old_fetch(mt5, symbol, day_start):
    """Frozen pre-WP2 reference; do not import the new implementation."""
    ticks, gaps = {}, []
    flag = getattr(mt5, "COPY_TICKS_ALL", getattr(mt5, "COPY_TICKS_INFO", 0))
    for hour in range(24):
        start = day_start + timedelta(hours=hour)
        end = start + timedelta(hours=1)
        rows = mt5.copy_ticks_range(symbol, start, end, flag)
        if rows is None:
            gaps.append((start, end, "BROKER_HISTORY_UNAVAILABLE"))
            continue
        if len(rows) > ledger.MAX_TICKS_PER_HOUR:
            gaps.append((start, end, "TICK_HOUR_OVER_LIMIT"))
            continue
        lower, upper = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
        kept = 0
        for row in rows:
            try:
                msc = int(row["time_msc"])
                bid, ask = float(row["bid"]), float(row["ask"])
                flags = int(row["flags"]) if "flags" in row.keys() else 0
            except (KeyError, TypeError, ValueError, IndexError):
                continue
            if lower <= msc < upper and math.isfinite(bid) and math.isfinite(ask):
                ticks[(msc, bid, ask)] = (msc, bid, ask, flags)
                kept += 1
        if kept == 0 and ledger.fx_session_open(start) and ledger.fx_session_open(end - timedelta(minutes=1)):
            gaps.append((start, end, "BROKER_SERVER_EMPTY"))
    return [ticks[key] for key in sorted(ticks)], gaps


def old_gzip(path, ticks):
    """Frozen pre-WP2 writer, including ASCII CSV and gzip settings."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("time_msc", "bid", "ask", "flags"))
    for msc, bid, ask, flags in ticks:
        writer.writerow((msc, repr(bid), repr(ask), flags))
    raw = buffer.getvalue().encode("ascii")
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", fileobj=handle, mode="wb", mtime=0) as archive:
            archive.write(raw)
    return hashlib.sha256(raw).hexdigest()


class FakeHistory:
    COPY_TICKS_ALL = 1

    def __init__(self, *, gaps=(), empty=(), records=3):
        self.gaps, self.empty, self.records = set(gaps), set(empty), records

    def copy_ticks_range(self, symbol, start, end, flag):
        if start.hour in self.gaps:
            return None
        if start.hour in self.empty:
            return []
        msc = int(start.timestamp() * 1000) + 1000
        return [
            {"time_msc": msc, "bid": 1.11, "ask": 1.12, "flags": 6},
            {"time_msc": msc, "bid": 1.11, "ask": 1.12, "flags": 8},
            {"time_msc": msc + 500, "bid": 1.115, "ask": 1.125, "flags": 6},
            {"time_msc": int(end.timestamp() * 1000), "bid": 1.10, "ask": 1.11, "flags": 6},
        ] if self.records else []

    def symbol_info(self, symbol):
        return SimpleNamespace(trade_tick_size=0.01, point=0.01)


class StreamArchiveTests(unittest.TestCase):
    def test_matches_frozen_old_format_bytes_hash_and_gap_reasons(self):
        for gaps, empty in [((), ()), ((4, 5), (9,)), (tuple(range(24)), ())]:
            with self.subTest(gaps=gaps, empty=empty), tempfile.TemporaryDirectory() as tmp:
                broker = FakeHistory(gaps=gaps, empty=empty)
                old, old_gaps = old_fetch(broker, "EURUSD", DAY)
                golden = Path(tmp) / "gold.csv.gz"
                if old:
                    golden_sha = old_gzip(golden, old)
                actual = Path(tmp) / "actual.csv.gz"
                count, first, last, digest, found_gaps, index = ledger._download_day(
                    broker, "EURUSD", DAY, actual)
                self.assertEqual(found_gaps, old_gaps)
                self.assertEqual(count, len(old))
                if old:
                    self.assertEqual((first, last), (old[0][0], old[-1][0]))
                    self.assertEqual(digest, golden_sha)
                    self.assertEqual(actual.read_bytes(), golden.read_bytes())
                    self.assertEqual(ledger.read_ticks(actual), old)
                    self.assertEqual(sum(v["end_row"] - v["start_row"]
                                         for v in index.values()), len(old))
                else:
                    self.assertIsNone(digest)
                    self.assertFalse(actual.exists())
                self.assertFalse(actual.with_suffix(".tmp").exists())

    def test_reconciliation_parses_only_selected_hour_and_same_ms_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp, closing(sqlite3.connect(":memory:")) as db:
            broker = FakeHistory()
            now = DAY + timedelta(hours=10, seconds=1)
            msc = int((DAY + timedelta(hours=10)).timestamp() * 1000) + 1000
            ledger.record_snapshot(db, observed_utc=now, clock_shift_hours=3,
                                   cards={"EURUSD": {"action": "WAIT"}},
                                   quotes={"EURUSD": (1.11, 1.12, msc / 1000)})
            path = Path(tmp) / "ticks.csv.gz"
            n, first, last, sha, gaps, index = ledger._download_day(broker, "EURUSD", DAY, path)
            checked, matched = ledger._reconcile_archive(
                db, "EURUSD", "2026-10-20", path, index, 0.01)
            self.assertEqual((checked, matched), (1, 1))

    def test_two_million_ticks_day_under_50_megabytes(self):
        class Tick(tuple):
            __slots__ = ()
            fields = {"time_msc": 0, "bid": 1, "ask": 2, "flags": 3}

            def __getitem__(self, key):
                return tuple.__getitem__(self, self.fields[key])

            def keys(self):
                return self.fields

        class BigBroker(FakeHistory):
            def copy_ticks_range(self, symbol, start, end, flag):
                first = int(start.timestamp() * 1000)
                return [Tick((first + i * 43, 1.1, 1.1001, 6))
                        for i in range(83334)]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "two-million.csv.gz"
            tracemalloc.start()
            try:
                count, _, _, _, _, _ = ledger._download_day(
                    BigBroker(), "EURUSD", DAY, path)
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(count, 83334 * 24)
            self.assertLess(peak, 50 * 1024 * 1024,
                            f"peak RAM tracked {peak / (1024 * 1024):.1f} MiB")


if __name__ == "__main__":
    unittest.main()
