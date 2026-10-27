"""WP8a: closed development bars with frozen broker lineage, no holdout or orders."""
from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from katarina.research.dev_dataset import (
    DEV_CUTOFF_UTC, export_dev_bars, load_dev_dataset,
)
from katarina.research.validation import ValidationError

UTC = timezone.utc
DAY = datetime(2026, 10, 12, tzinfo=UTC)
FRAMES = {"M5": 300, "M15": 900, "H1": 3600, "H4": 14400}


def bar(at, *, spread=12):
    return {"time": int(at.timestamp()), "open": 1.1, "high": 1.2,
            "low": 1.0, "close": 1.15, "tick_volume": 8,
            "spread": spread, "real_volume": 0}


class FakeBroker:
    def __init__(self, *, contaminated=False):
        self.calls = []
        self.contaminated = contaminated

    def verified_historical_bar_shift(self, symbol, timeframe, start, end):
        # Fixture-only independent clock proof; production MT5 has no
        # such method and fails closed until external UTC proof is supplied.
        return dict(verified=True, time_basis="INDEPENDENT_UTC",
                    shift_hours=0, source_sha256="a" * 64)

    def symbol_info(self, symbol):
        return SimpleNamespace(point=0.00001, trade_tick_size=0.00001,
                               trade_contract_size=100000.0)

    def copy_rates_range(self, symbol, timeframe, start, end):
        self.calls.append((symbol, timeframe, start, end))
        if self.contaminated:
            return [bar(DEV_CUTOFF_UTC)]
        minute = FRAMES[timeframe]
        # Two bars from a single fully closed timeframe on Oct 12.
        return [bar(DAY), bar(DAY + timedelta(seconds=minute))]


class DevDatasetTests(unittest.TestCase):
    def test_no_independent_clock_evidence_fails_closed(self):
        class NoEvidenceBroker(FakeBroker):
            verified_historical_bar_shift = None

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValidationError, "BROKER_BAR_CLOCK_NOT_VERIFIED"):
                export_dev_bars(NoEvidenceBroker(), ("EURUSD.vx",),
                                start=DAY, end=DAY + timedelta(days=1), out=tmp)
            self.assertFalse((Path(tmp) / "manifest.json").exists())

    def test_server_shift_plus_three_is_converted_before_cutoff(self):
        class ShiftedBroker(FakeBroker):
            def verified_historical_bar_shift(self, symbol, timeframe, start, end):
                return dict(verified=True, time_basis="INDEPENDENT_UTC",
                            shift_hours=3, source_sha256="b" * 64)
            def copy_rates_range(self, symbol, timeframe, start, end):
                rows = super().copy_rates_range(symbol, timeframe, start, end)
                return [{**row, "time":row["time"] + 3*3600} for row in rows]

        with tempfile.TemporaryDirectory() as tmp:
            manifest = export_dev_bars(ShiftedBroker(), ("EURUSD.vx",),
                                       start=DAY, end=DAY + timedelta(days=1), out=tmp)
            self.assertEqual(load_dev_dataset(tmp)["EURUSD.vx"]["M5"][0]["time_utc"],
                             DAY.isoformat())
            proof = manifest["files"]["EURUSD.vx/M5.csv.gz"]["clock_evidence"]
            self.assertEqual(proof[0]["shift_hours"], 3)

    def test_dst_shift_can_change_on_separate_verified_chunks(self):
        origin = datetime(2025, 10, 25, tzinfo=UTC)
        class DstBroker(FakeBroker):
            def verified_historical_bar_shift(self, symbol, timeframe, start, end):
                shift = 3 if start.day == 25 else 2
                return dict(verified=True, time_basis="INDEPENDENT_UTC",
                            shift_hours=shift, source_sha256="c" * 64)
            def copy_rates_range(self, symbol, timeframe, start, end):
                seconds = FRAMES[timeframe]
                return [bar(start), bar(start + timedelta(seconds=seconds))]

        with tempfile.TemporaryDirectory() as tmp:
            manifest = export_dev_bars(
                DstBroker(), ("EURUSD.vx",), start=origin,
                end=origin + timedelta(days=2), chunk_days=1, out=tmp)
            proof = manifest["files"]["EURUSD.vx/M5.csv.gz"]["clock_evidence"]
            self.assertEqual([row["shift_hours"] for row in proof], [3, 2])
            bars = load_dev_dataset(tmp)["EURUSD.vx"]["M5"]
            self.assertEqual(bars[0]["time_utc"], origin.isoformat())
            self.assertEqual(bars[2]["time_utc"],
                             (origin + timedelta(days=1)).isoformat())

    def test_unverified_proof_is_rejected(self):
        class BadProof(FakeBroker):
            def verified_historical_bar_shift(self, symbol, timeframe, start, end):
                return dict(verified=False, shift_hours=3,
                            time_basis="INDEPENDENT_UTC", source_sha256="a" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValidationError, "BROKER_BAR_CLOCK_NOT_VERIFIED"):
                export_dev_bars(BadProof(), ("EURUSD.vx",),
                                start=DAY, end=DAY + timedelta(days=1), out=tmp)

    def test_cutoff_is_rejected_at_export_even_if_broker_returns_future(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValidationError, "holdout_data_forbidden"):
                export_dev_bars(FakeBroker(contaminated=True), ("EURUSD.vx",),
                                start=DAY, end=DEV_CUTOFF_UTC, out=tmp)
            self.assertFalse((Path(tmp) / "manifest.json").exists())

    def test_date_validation_blocks_naive_and_holdout_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            for start, end in [
                (DAY.replace(tzinfo=None), DEV_CUTOFF_UTC),
                (DAY, DEV_CUTOFF_UTC + timedelta(seconds=1)),
                (DEV_CUTOFF_UTC, DEV_CUTOFF_UTC),
            ]:
                with self.subTest(start=start, end=end), self.assertRaises(
                        (ValidationError, ValueError)):
                    export_dev_bars(FakeBroker(), ("EURUSD.vx",),
                                    start=start, end=end, out=tmp)

    def test_export_roundtrip_hash_manifest_order_spread_and_closed_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            broker = FakeBroker()
            manifest = export_dev_bars(broker, ("XAUUSD.vx", "EURUSD.vx"),
                                       start=DAY, end=DAY + timedelta(days=1), out=tmp)
            self.assertEqual(len(broker.calls), 8)
            self.assertEqual(sorted(manifest["files"]), [
                f"{s}/{t}.csv.gz" for s in ("EURUSD.vx", "XAUUSD.vx")
                for t in sorted(FRAMES)])
            dataset = load_dev_dataset(tmp)
            self.assertEqual(set(dataset), {"XAUUSD.vx", "EURUSD.vx"})
            self.assertEqual(len(dataset["EURUSD.vx"]["M5"]), 2)
            self.assertEqual(dataset["EURUSD.vx"]["M5"][0]["spread"], 12)
            self.assertEqual(dataset["EURUSD.vx"]["M5"][0]["closed_at_utc"],
                             "2026-10-12T00:05:00+00:00")
            self.assertEqual(len(manifest["manifest_sha256"]), 64)
            self.assertEqual(manifest["files"]["EURUSD.vx/M5.csv.gz"]["bars"], 2)
            self.assertFalse(manifest["live_execution_authorized"])

    def test_missing_bars_are_gaps_not_interpolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = export_dev_bars(FakeBroker(), ("EURUSD.vx",), start=DAY,
                                       end=DAY + timedelta(days=1), out=tmp)
            gaps = manifest["files"]["EURUSD.vx/M5.csv.gz"]["gaps"]
            self.assertIn({
                "start_utc": "2026-10-12T00:10:00+00:00",
                "end_utc": "2026-10-13T00:00:00+00:00",
                "reason": "BROKER_BAR_GAP"}, gaps)
            self.assertEqual(len(load_dev_dataset(tmp)["EURUSD.vx"]["M5"]), 2)

    def test_same_broker_data_produces_identical_gzip_and_manifest_hash(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a = export_dev_bars(FakeBroker(), ("EURUSD.vx",),
                                start=DAY, end=DAY + timedelta(days=1), out=first)
            b = export_dev_bars(FakeBroker(), ("EURUSD.vx",),
                                start=DAY, end=DAY + timedelta(days=1), out=second)
            self.assertEqual(a, b)
            self.assertEqual((Path(first) / "EURUSD.vx/M5.csv.gz").read_bytes(),
                             (Path(second) / "EURUSD.vx/M5.csv.gz").read_bytes())

    def test_archives_are_hashed_and_loaded_without_reading_entire_gzip(self):
        from unittest.mock import patch

        original = Path.read_bytes

        def reject_full_archive_read(path):
            if path.name.endswith(".csv.gz"):
                raise AssertionError("unbounded_archive_read")
            return original(path)

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(Path, "read_bytes", reject_full_archive_read):
                export_dev_bars(FakeBroker(), ("EURUSD.vx",), start=DAY,
                                end=DAY + timedelta(days=1), out=tmp)
                dataset = load_dev_dataset(tmp)
        self.assertEqual(len(dataset["EURUSD.vx"]["M5"]), 2)

    def test_tampered_file_or_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_dev_bars(FakeBroker(), ("EURUSD.vx",), start=DAY,
                            end=DAY + timedelta(days=1), out=root)
            file = root / "EURUSD.vx/M5.csv.gz"
            file.write_bytes(file.read_bytes() + b"bad")
            with self.assertRaises(ValidationError):
                load_dev_dataset(root)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_dev_bars(FakeBroker(), ("EURUSD.vx",), start=DAY,
                            end=DAY + timedelta(days=1), out=root)
            path = root / "manifest.json"
            j = json.loads(path.read_text(encoding="utf-8"))
            j["files"]["EURUSD.vx/M5.csv.gz"]["bars"] = 500
            path.write_text(json.dumps(j), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_dev_dataset(root)

    def test_loader_rejects_holdout_bar_even_when_attacker_updates_both_hashes(self):
        from katarina.research import validation as v
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_dev_bars(FakeBroker(), ("EURUSD.vx",), start=DAY,
                            end=DAY + timedelta(days=1), out=root)
            data_path = root / "EURUSD.vx/M5.csv.gz"
            with gzip.open(data_path, "rt", encoding="ascii", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["time_utc"] = DEV_CUTOFF_UTC.isoformat()
            rows[0]["closed_at_utc"] = (DEV_CUTOFF_UTC + timedelta(minutes=5)).isoformat()
            header = list(rows[0])
            import io
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            with data_path.open("wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as out:
                    out.write(buf.getvalue().encode("ascii"))
            mpath = root / "manifest.json"
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
            record = manifest["files"]["EURUSD.vx/M5.csv.gz"]
            record["sha256"] = hashlib.sha256(data_path.read_bytes()).hexdigest()
            record["bytes"] = data_path.stat().st_size
            manifest.pop("manifest_sha256")
            manifest["manifest_sha256"] = v.sha256_text(v.canonical(manifest))
            mpath.write_text(v.canonical(manifest) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "holdout_data_forbidden"):
                load_dev_dataset(root)


if __name__ == "__main__":
    unittest.main()
