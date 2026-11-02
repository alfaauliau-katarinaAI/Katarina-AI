import gzip
import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from katarina.intelligence.operations import candidate_ledger, observation_ledger
from katarina.research import validation as v
from scripts.research.export_candidates import export_candidates_to_trades


class ExportCandidatesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state_dir = self.root / "state"
        self.state_dir.mkdir(parents=True)
        self.db_path = self.state_dir / "context.sqlite3"
        self.db = sqlite3.connect(str(self.db_path))
        candidate_ledger.setup(self.db)
        observation_ledger.setup(self.db)

        self.registry_path = self.root / "registry.jsonl"
        self.registry = v.HypothesisRegistry(self.registry_path)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def _write_tick_file(self, symbol: str, day: str, ticks: list[tuple[int, float, float]]) -> tuple[str, str]:
        rel_path = f"broker-ticks/{symbol}/{day}.csv.gz"
        full_path = self.state_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        lines = ["time_msc,bid,ask,flags\n"]
        for msc, bid, ask in ticks:
            lines.append(f"{msc},{bid:.5f},{ask:.5f},6\n")
        content = "".join(lines).encode("ascii")
        sha256 = hashlib.sha256(content).hexdigest()

        with gzip.open(full_path, "wb") as gz:
            gz.write(content)

        return rel_path, sha256

    def test_export_trades_from_candidates_with_hypothesis_exit_rules(self):
        # 1. Register hypothesis with strict exit_rules
        spec = {
            "name": "test_candidate_export_v1",
            "symbol": "EURUSD",
            "side": "BUY",
            "regime": "TREND_UP",
            "playbook": "PULLBACK",
            "rules": "entry_on_m5_pullback",
            "parameters": {
                "exit_rules": {
                    "use_target": True,
                    "use_invalidation": True,
                    "max_holding_seconds": 3600,
                }
            },
        }
        entry = self.registry.register(spec, registered_utc=datetime(2026, 1, 1, tzinfo=timezone.utc))
        hyp_id = entry["hypothesis_id"]

        # 2. Insert candidate row
        cards = {
            "EURUSD": {
                "observed_vps_timestamp_utc": "2026-10-20T10:00:00Z",
                "closed_bar_times_utc": {"M5": "2026-10-20T09:55:00Z"},
                "market_state": "TREND_UP",
                "direction_bias": "BUY",
                "selected_method": "PULLBACK",
                "technical_setup": "M5_PULLBACK",
                "action": "WAIT",
                "conditional_side": "BUY",
                "conditional_invalidation": 1.05000,
                "conditional_target": 1.06000,
                "after_spread_rr_geometry": 2.0,
                "blocking_reasons": ["macro_blackout"],
            }
        }
        quotes = {"EURUSD": (1.05200, 1.05210, 1792490400.0)}
        candidate_ledger.record(self.db, cycle_id="c-20261020T100000.000Z", cards=cards, quotes=quotes)

        # 3. Write verified broker tick file
        entry_msc = int(datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        ticks = [
            (entry_msc + 1000, 1.05220, 1.05230),
            (entry_msc + 2000, 1.05500, 1.05510),
            (entry_msc + 3000, 1.06010, 1.06020),  # hits target (1.06000)
        ]
        rel_path, sha256 = self._write_tick_file("EURUSD", "2026-10-20", ticks)

        with self.db:
            self.db.execute(
                "INSERT INTO broker_tick_days(symbol, day, status, sha256, file) VALUES(?,?,?,?,?)",
                ("EURUSD", "2026-10-20", "STORED", sha256, rel_path),
            )

        out_trades = self.root / "trades.jsonl"
        summary = export_candidates_to_trades(
            state_dir=self.state_dir,
            registry_path=self.registry_path,
            hypothesis_id=hyp_id,
            output_trades_path=out_trades,
        )

        self.assertEqual(summary["orders_submitted"], 0)
        self.assertFalse(summary["live_execution_authorized"])
        self.assertEqual(summary["trades_exported"], 1)

        lines = out_trades.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        trade_data = json.loads(lines[0])
        trade = v.Trade.from_dict(trade_data)
        self.assertEqual(trade.side, "BUY")
        self.assertEqual(trade.entry_mid, 1.05205)
        self.assertEqual(trade.exit_mid, 1.06000)
        # data_until must be <= entry_at
        self.assertLessEqual(trade.data_until, trade.entry_at)

    def test_export_trades_fails_when_tick_file_hash_mismatch(self):
        spec = {
            "name": "test_hash_check_v1",
            "symbol": "EURUSD",
            "side": "BUY",
            "regime": "TREND_UP",
            "playbook": "PULLBACK",
            "rules": "entry_on_m5_pullback",
            "parameters": {
                "exit_rules": {
                    "use_target": True,
                    "use_invalidation": True,
                    "max_holding_seconds": 3600,
                }
            },
        }
        entry = self.registry.register(spec, registered_utc=datetime(2026, 1, 1, tzinfo=timezone.utc))
        hyp_id = entry["hypothesis_id"]

        cards = {
            "EURUSD": {
                "observed_vps_timestamp_utc": "2026-10-20T10:00:00Z",
                "closed_bar_times_utc": {"M5": "2026-10-20T09:55:00Z"},
                "market_state": "TREND_UP",
                "direction_bias": "BUY",
                "selected_method": "PULLBACK",
                "technical_setup": "M5_PULLBACK",
                "action": "WAIT",
                "conditional_side": "BUY",
                "conditional_invalidation": 1.05000,
                "conditional_target": 1.06000,
            }
        }
        quotes = {"EURUSD": (1.05200, 1.05210, 1792490400.0)}
        candidate_ledger.record(self.db, cycle_id="c-20261020T100000.000Z", cards=cards, quotes=quotes)

        # Write ticks but store wrong sha256 in broker_tick_days
        entry_msc = int(datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        ticks = [(entry_msc + 1000, 1.05220, 1.05230)]
        rel_path, _ = self._write_tick_file("EURUSD", "2026-10-20", ticks)

        with self.db:
            self.db.execute(
                "INSERT INTO broker_tick_days(symbol, day, status, sha256, file) VALUES(?,?,?,?,?)",
                ("EURUSD", "2026-10-20", "STORED", "deadbeef" * 8, rel_path),
            )

        with self.assertRaises(v.ValidationError) as ctx:
            export_candidates_to_trades(
                state_dir=self.state_dir,
                registry_path=self.registry_path,
                hypothesis_id=hyp_id,
                output_trades_path=self.root / "trades.jsonl",
            )
        self.assertIn("TICK_FILE_HASH_MISMATCH", str(ctx.exception))

    def test_export_trades_fails_when_hypothesis_missing_exit_rules(self):
        spec = {
            "name": "test_no_exit_rules_v1",
            "symbol": "EURUSD",
            "side": "BUY",
            "regime": "TREND_UP",
            "playbook": "PULLBACK",
            "rules": "entry_on_m5_pullback",
            "parameters": {},  # Missing exit_rules
        }
        entry = self.registry.register(spec, registered_utc=datetime(2026, 1, 1, tzinfo=timezone.utc))
        hyp_id = entry["hypothesis_id"]

        with self.assertRaises(v.ValidationError) as ctx:
            export_candidates_to_trades(
                state_dir=self.state_dir,
                registry_path=self.registry_path,
                hypothesis_id=hyp_id,
                output_trades_path=self.root / "trades.jsonl",
            )
        self.assertIn("EXIT_RULES_SPEC_REQUIRED", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
