"""Context export from Stage 0 tick files: lineage, causality, gaps and Stage 2 compatibility.

Synthetic ticks test the TOOL; nothing here is market evidence.
"""
import gzip
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.intelligence.operations import observation_ledger as ledger
from katarina.research import validation as v
from katarina.research.context_export import export_contexts
from katarina.research.market_intelligence import MarketContext

UTC = timezone.utc
SYMBOL = "XAUUSD.SYNTH"
SPLIT = v.DataSplit(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 4, 1, tzinfo=UTC),
                    datetime(2026, 4, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC),
                    gaps=((datetime(2026, 2, 10, tzinfo=UTC), datetime(2026, 2, 11, tzinfo=UTC), "OBSERVER_DOWN"),))
PARAMS = dict(symbol=SYMBOL, split=SPLIT, lookback_minutes=60, bar_minutes=5, atr_bars=6)


def day_ticks(day: datetime):
    """One tick every 10 s; price walks up and down so every 5-minute bar has a range."""
    rows = []
    for k in range(0, 24 * 360):
        msc = int((day + timedelta(seconds=10 * k)).timestamp() * 1000)
        bid = 2000.0 + (k % 30) * 0.1
        rows.append((msc, bid, bid + 0.2, 0))
    return rows


def signal(tid, at):
    return v.Trade(tid, "BUY", at, at + timedelta(hours=1), at + timedelta(hours=1), at - timedelta(seconds=1),
                   2000.0, 2001.0, 5.0, 0.2, 0.2, "BUY")


class ContextExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        ledger.setup(self.db)
        for day in (datetime(2026, 1, 5, tzinfo=UTC), datetime(2026, 1, 6, tzinfo=UTC)):
            self.store(day)

    def store(self, day, status="STORED"):
        key = day.date().isoformat()
        path = ledger.tick_path(self.root, SYMBOL, key)
        digest = ledger._write_ticks(path, day_ticks(day))
        self.db.execute("INSERT INTO broker_tick_days(symbol, day, status, sha256, file) VALUES(?,?,?,?,?)",
                        (SYMBOL, key, status, digest, path.relative_to(self.root).as_posix()))

    def export(self, signals, **overrides):
        return export_contexts(self.db, self.root, signals, **{**PARAMS, **overrides})

    def test_contexts_are_causal_verified_and_stage2_compatible(self):
        at = datetime(2026, 1, 5, 9, 0, 5, tzinfo=UTC)
        rows, manifest = self.export([signal("a", at)])
        self.assertEqual(manifest["contexts"], 1)
        row = rows[0]
        context = MarketContext(**row)  # the Stage 2 loader accepts the row unchanged
        self.assertLess(context.observed_at, at)
        self.assertEqual(context.window_start, at - timedelta(minutes=60))
        self.assertEqual(context.tick_count, 360)  # 60 minutes at one tick per 10 s, all before entry
        self.assertGreater(context.atr_price, 0)
        self.assertEqual(manifest["tick_sources"], [{"day": "2026-01-05", "sha256": manifest["tick_sources"][0]["sha256"]}])
        self.assertFalse(manifest["live_execution_authorized"])

    def test_window_spanning_midnight_reads_both_days(self):
        rows, manifest = self.export([signal("m", datetime(2026, 1, 6, 0, 20, tzinfo=UTC))])
        self.assertEqual(manifest["contexts"], 1)
        self.assertEqual([s["day"] for s in manifest["tick_sources"]], ["2026-01-05", "2026-01-06"])

    def test_ticks_at_or_after_entry_never_change_the_context(self):
        at = datetime(2026, 1, 5, 9, 0, 0, tzinfo=UTC)
        first, _ = self.export([signal("c", at)])
        # Rewrite the day with a wild price spike from the entry onward; context must not move.
        key, path = "2026-01-05", ledger.tick_path(self.root, SYMBOL, "2026-01-05")
        ticks = [(m, b + (500 if m >= at.timestamp() * 1000 else 0), a + (500 if m >= at.timestamp() * 1000 else 0), f)
                 for m, b, a, f in day_ticks(datetime(2026, 1, 5, tzinfo=UTC))]
        digest = ledger._write_ticks(path, ticks)
        self.db.execute("UPDATE broker_tick_days SET sha256=? WHERE day=?", (digest, key))
        second, _ = self.export([signal("c", at)])
        for field in ("observed_at", "range_price", "atr_price", "tick_count"):
            self.assertEqual(first[0][field], second[0][field])

    def test_open_bar_before_entry_does_not_change_range_or_atr(self):
        at = datetime(2026, 1, 5, 9, 2, 30, tzinfo=UTC)  # the 09:00-09:05 bar is still open
        first, _ = self.export([signal("o", at)])
        open_bar = datetime(2026, 1, 5, 9, 0, tzinfo=UTC).timestamp() * 1000
        ticks = [(m, b + (50 if m >= open_bar else 0), a + (50 if m >= open_bar else 0), f)
                 for m, b, a, f in day_ticks(datetime(2026, 1, 5, tzinfo=UTC))]
        digest = ledger._write_ticks(ledger.tick_path(self.root, SYMBOL, "2026-01-05"), ticks)
        self.db.execute("UPDATE broker_tick_days SET sha256=? WHERE day='2026-01-05'", (digest,))
        second, _ = self.export([signal("o", at)])
        self.assertEqual((first[0]["range_price"], first[0]["atr_price"]),
                         (second[0]["range_price"], second[0]["atr_price"]))

    def test_tampered_tick_file_is_refused(self):
        path = ledger.tick_path(self.root, SYMBOL, "2026-01-05")
        raw = gzip.decompress(path.read_bytes()).replace(b"2000.0", b"2000.5", 1)
        path.write_bytes(gzip.compress(raw))
        rows, manifest = self.export([signal("t", datetime(2026, 1, 5, 9, tzinfo=UTC))])
        self.assertEqual(rows, [])
        self.assertEqual(manifest["missing_reasons"], {"TICK_FILE_HASH_MISMATCH": 1})

    def test_gaps_missing_days_and_holdout_get_no_context(self):
        self.db.execute("INSERT INTO data_gaps(stream, symbol, start_utc, end_utc, reason, recorded_utc) "
                        "VALUES('broker_ticks', ?, ?, ?, 'BROKER_SERVER_EMPTY', ?)",
                        (SYMBOL, "2026-01-06T10:00:00+00:00", "2026-01-06T11:00:00+00:00", "2026-01-07T00:00:00+00:00"))
        signals = [signal("gap", datetime(2026, 1, 6, 10, 30, tzinfo=UTC)),
                   signal("noday", datetime(2026, 1, 8, 9, tzinfo=UTC)),
                   signal("split-gap", datetime(2026, 2, 10, 9, tzinfo=UTC)),
                   signal("holdout", datetime(2026, 4, 2, 9, tzinfo=UTC)),
                   signal("early", datetime(2026, 1, 5, 0, 30, tzinfo=UTC))]
        rows, manifest = self.export(signals)
        self.assertEqual(rows, [])
        self.assertEqual({m["trade_id"]: m["reason"] for m in manifest["missing"]}, {
            "gap": "BROKER_TICK_GAP_IN_WINDOW", "noday": "TICK_DAY_NOT_STORED",
            "split-gap": "WINDOW_OUTSIDE_DEVELOPMENT_OR_IN_GAP",
            "holdout": "WINDOW_OUTSIDE_DEVELOPMENT_OR_IN_GAP", "early": "TICK_DAY_NOT_STORED"})

    def test_unusable_status_and_bad_parameters(self):
        self.db.execute("UPDATE broker_tick_days SET status='GAP' WHERE day='2026-01-05'")
        rows, manifest = self.export([signal("g", datetime(2026, 1, 5, 9, tzinfo=UTC))])
        self.assertEqual(manifest["missing_reasons"], {"TICK_DAY_NOT_STORED": 1})
        with self.assertRaises(v.ValidationError):
            self.export([], lookback_minutes=10)  # shorter than bar_minutes * atr_bars

    def test_export_is_deterministic(self):
        signals = [signal(str(h), datetime(2026, 1, 5, h, tzinfo=UTC)) for h in range(2, 20, 3)]
        first, a = self.export(signals)
        second, b = self.export(list(reversed(signals)))
        self.assertEqual(first, second)
        self.assertEqual(a["manifest_sha256"], b["manifest_sha256"])


if __name__ == "__main__":
    unittest.main()
