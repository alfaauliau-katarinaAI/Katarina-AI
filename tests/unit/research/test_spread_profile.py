"""Unit tests for research.spread_profile and iter_verified_ticks (docs/ROADMAP.md WP10a)."""
from __future__ import annotations

import contextlib
import datetime
import gzip
import hashlib
import json
import sqlite3
import tempfile
import tracemalloc
import unittest
from pathlib import Path

from katarina.research import validation as v
from katarina.research.context_export import _ticks, iter_verified_ticks
from katarina.research.spread_profile import (
    LABEL,
    USAGE,
    build_spread_profile,
    nearest_rank_percentile,
)


def create_synthetic_tick_file(path: Path, ticks: list[tuple[int, float, float]]) -> str:
    """Write synthetic tick CSV gzip and return sha256 digest of decompressed content."""
    lines = ["time_msc,bid,ask,flags"]
    for msc, bid, ask in ticks:
        lines.append(f"{msc},{bid:.5f},{ask:.5f},0")
    decompressed = ("\n".join(lines) + "\n").encode("ascii")
    digest = hashlib.sha256(decompressed).hexdigest()

    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(filename=str(path), mode="wb", mtime=0) as gz:
        gz.write(decompressed)
    return digest


class SpreadProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_hash_mismatch_rejected(self):
        tick_file = self.root / "broker-ticks" / "EURUSD" / "2026-10-22.csv.gz"
        create_synthetic_tick_file(tick_file, [(1792627200000, 1.1000, 1.1002)])
        record = {
            "file": "broker-ticks/EURUSD/2026-10-22.csv.gz",
            "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        }
        with self.assertRaises(v.ValidationError) as ctx:
            list(iter_verified_ticks(self.root, record))
        self.assertEqual(str(ctx.exception), "TICK_FILE_HASH_MISMATCH")

        with self.assertRaises(v.ValidationError) as ctx2:
            _ticks(self.root, record)
        self.assertEqual(str(ctx2.exception), "TICK_FILE_HASH_MISMATCH")

    def test_ticks_parity(self):
        tick_file = self.root / "broker-ticks" / "EURUSD" / "2026-10-22.csv.gz"
        raw_ticks = [
            (1792627200000, 1.1000, 1.1002),
            (1792627201000, 1.1001, 1.1005),
            (1792627202000, 1.1002, 1.1004),
        ]
        digest = create_synthetic_tick_file(tick_file, raw_ticks)
        record = {"file": "broker-ticks/EURUSD/2026-10-22.csv.gz", "sha256": digest}

        iter_out = list(iter_verified_ticks(self.root, record))
        self.assertEqual(iter_out, raw_ticks)

        ticks_out = _ticks(self.root, record)
        expected_mids = [(msc, (bid + ask) / 2) for msc, bid, ask in raw_ticks]
        self.assertEqual(ticks_out, expected_mids)

    def test_one_quote_per_minute_sampling(self):
        # 3 ticks in same minute 10:05 UTC (1792663500000 ms = 2026-10-22 10:05:00)
        base_msc = 1792663500000
        ticks = [
            (base_msc, 1.10000, 1.10010),        # spread 0.00010
            (base_msc + 20000, 1.10000, 1.10020), # spread 0.00020
            (base_msc + 59000, 1.10000, 1.10030), # spread 0.00030 (LAST in minute)
        ]
        tick_file = self.root / "broker-ticks" / "EURUSD" / "2026-10-22.csv.gz"
        digest = create_synthetic_tick_file(tick_file, ticks)

        db_path = self.root / "context.sqlite3"
        with contextlib.closing(sqlite3.connect(db_path)) as db:
            db.execute("CREATE TABLE broker_tick_days(symbol TEXT, day TEXT, status TEXT, sha256 TEXT, file TEXT)")
            db.execute("INSERT INTO broker_tick_days VALUES('EURUSD', '2026-10-22', 'STORED', ?, ?)",
                       (digest, "broker-ticks/EURUSD/2026-10-22.csv.gz"))
            db.commit()

        report = build_spread_profile(self.root, "2026-10-22", "2026-10-22")
        summary = report["symbols"]["EURUSD"]["summary"]
        self.assertEqual(summary["minutes"], 1)
        self.assertAlmostEqual(summary["max"], 0.00030)
        self.assertAlmostEqual(summary["p50"], 0.00030)

        hour_10 = report["symbols"]["EURUSD"]["hourly"]["10"]
        self.assertEqual(hour_10["minutes"], 1)
        self.assertAlmostEqual(hour_10["max"], 0.00030)

    def test_nearest_rank_percentiles_deterministic(self):
        # 10 values: 0.00010 to 0.00100
        values = [i * 0.00010 for i in range(1, 11)]
        self.assertAlmostEqual(nearest_rank_percentile(values, 50.0), 0.00050)
        self.assertAlmostEqual(nearest_rank_percentile(values, 90.0), 0.00090)
        self.assertAlmostEqual(nearest_rank_percentile(values, 99.0), 0.00100)
        self.assertEqual(nearest_rank_percentile([], 50.0), 0.0)

    def test_date_bounds_inclusive(self):
        db_path = self.root / "context.sqlite3"
        with contextlib.closing(sqlite3.connect(db_path)) as db:
            db.execute("CREATE TABLE broker_tick_days(symbol TEXT, day TEXT, status TEXT, sha256 TEXT, file TEXT)")

            for day in ("2026-10-21", "2026-10-22", "2026-10-23"):
                rel = f"broker-ticks/EURUSD/{day}.csv.gz"
                p = self.root / rel
                msc = int(datetime.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
                digest = create_synthetic_tick_file(p, [(msc, 1.1000, 1.1002)])
                db.execute("INSERT INTO broker_tick_days VALUES('EURUSD', ?, 'STORED', ?, ?)", (day, digest, rel))
            db.commit()

        report = build_spread_profile(self.root, "2026-10-22", "2026-10-22")
        self.assertEqual(len(report["sources"]), 1)
        self.assertEqual(report["sources"][0]["day"], "2026-10-22")
        self.assertEqual(report["period"], {"since": "2026-10-22", "until": "2026-10-22"})
        self.assertEqual(report["usage"], USAGE)
        self.assertEqual(report["label"], LABEL)

    def test_streaming_2m_ticks_tracemalloc_peak(self):
        tick_file = self.root / "broker-ticks" / "EURUSD" / "2026-10-22.csv.gz"
        tick_file.parent.mkdir(parents=True, exist_ok=True)

        header = b"time_msc,bid,ask,flags\n"
        hasher = hashlib.sha256()
        hasher.update(header)

        base_msc = 1792627200000  # 2026-10-22 00:00:00 UTC
        total_ticks = 2_000_000

        with gzip.GzipFile(filename=str(tick_file), mode="wb", mtime=0) as gz:
            gz.write(header)
            for i in range(total_ticks):
                msc = base_msc + i * 35  # ~19.4 hours
                line = f"{msc},1.10000,1.10020,0\n".encode("ascii")
                hasher.update(line)
                gz.write(line)

        digest = hasher.hexdigest()

        db_path = self.root / "context.sqlite3"
        with contextlib.closing(sqlite3.connect(db_path)) as db:
            db.execute("CREATE TABLE broker_tick_days(symbol TEXT, day TEXT, status TEXT, sha256 TEXT, file TEXT)")
            db.execute("INSERT INTO broker_tick_days VALUES('EURUSD', '2026-10-22', 'STORED', ?, ?)",
                       (digest, "broker-ticks/EURUSD/2026-10-22.csv.gz"))
            db.commit()

        tracemalloc.start()
        try:
            report = build_spread_profile(self.root, "2026-10-22", "2026-10-22")
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        self.assertLess(peak_mb, 50.0, f"Tracemalloc peak memory {peak_mb:.2f} MB exceeds 50MB limit")
        self.assertIn("EURUSD", report["symbols"])

    def test_connection_always_closed(self):
        db_path = self.root / "context.sqlite3"
        with contextlib.closing(sqlite3.connect(db_path)) as db:
            db.execute("CREATE TABLE broker_tick_days(symbol TEXT, day TEXT, status TEXT, sha256 TEXT, file TEXT)")
            db.commit()

        report = build_spread_profile(self.root, "2026-10-22", "2026-10-22")
        self.assertEqual(report["sources"], [])
        with contextlib.closing(sqlite3.connect(db_path)) as db:
            db.execute("INSERT INTO broker_tick_days VALUES('EURUSD', '2026-10-22', 'STORED', 'a', 'b')")
            db.commit()

    def test_identical_result_on_same_input(self):
        db_path = self.root / "context.sqlite3"
        tick_file = self.root / "broker-ticks" / "EURUSD" / "2026-10-22.csv.gz"
        digest = create_synthetic_tick_file(tick_file, [(1792627200000, 1.1000, 1.1002)])

        with contextlib.closing(sqlite3.connect(db_path)) as db:
            db.execute("CREATE TABLE broker_tick_days(symbol TEXT, day TEXT, status TEXT, sha256 TEXT, file TEXT)")
            db.execute("INSERT INTO broker_tick_days VALUES('EURUSD', '2026-10-22', 'STORED', ?, ?)",
                       (digest, "broker-ticks/EURUSD/2026-10-22.csv.gz"))
            db.commit()

        report1 = build_spread_profile(self.root, "2026-10-22", "2026-10-22")
        report2 = build_spread_profile(self.root, "2026-10-22", "2026-10-22")

        self.assertEqual(report1, report2)
        self.assertEqual(
            json.dumps(report1, sort_keys=True),
            json.dumps(report2, sort_keys=True),
        )


if __name__ == "__main__":
    unittest.main()
