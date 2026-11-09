"""D9 CLI keeps real files read-only; fixtures here are entirely synthetic."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from katarina.intelligence.operations import observation_ledger
from scripts.ai import check_stage0_health, preview_broker_sessions


class BrokerSessionPreviewCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db_path = self.root / "context.sqlite3"
        self.symbols = json.loads(preview_broker_sessions.UNIVERSE_PATH.read_bytes())["core"]
        from datetime import datetime
        with contextlib.closing(sqlite3.connect(self.db_path)) as db, db:
            observation_ledger.setup(db)
            for stamp, missing in (("2026-11-05T22:30:00Z", ("XAUUSD.vx",)),
                                   ("2026-11-05T22:31:00Z", ("XAUUSD.vx", "EURUSD.vx"))):
                moment = datetime.fromisoformat(stamp)
                cid = observation_ledger.record_snapshot(db, observed_utc=moment, clock_shift_hours=2,
                    cards={s: {} for s in self.symbols},
                    quotes={s: (1.0, 1.1, moment.timestamp()) for s in self.symbols if s not in missing})
                observation_ledger.close_cycle(db, cycle_id=cid, finished_utc=moment, status="PARTIAL",
                                               reason="SOME_SYMBOLS_WITHOUT_QUOTE")
        self.schedule = {
            "schema_version": 1, "broker_server_sha256": "a" * 64, "source_sha256": "b" * 64,
            "captured_at_utc": "2026-11-05T00:00:00Z", "valid_from_utc": "2026-11-05T00:00:00Z",
            "valid_until_utc": "2026-11-07T00:00:00Z", "verified_broker_dates": ["2026-11-05", "2026-11-06"],
            "symbols": {s: {"quote": {str(d): [[start, 86100]] for d in range(7)}}
                        for s in self.symbols
                        for start in [0 if s in ("EURUSD.vx", "GBPUSD.vx", "USDJPY.vx") else 3600]}}
        self.clock = {"schema_version": 1, "broker_server_sha256": "a" * 64, "intervals": [{
            "start_utc": "2026-11-05T00:00:00Z", "end_utc": "2026-11-07T00:00:00Z",
            "offset_seconds": 7200, "reason": "LIVE_FEED_CLOCK_VERIFIED", "evidence_sha256": "c" * 64}]}
        self.schedule_path = self.root / "schedule.json"
        self.clock_path = self.root / "clock.json"
        self.write_inputs()

    def write_inputs(self):
        self.schedule_path.write_text(json.dumps(self.schedule), encoding="utf-8")
        self.clock_path.write_text(json.dumps(self.clock), encoding="utf-8")

    def args(self, *extra):
        return ["--state-dir", str(self.root), "--schedule", str(self.schedule_path),
                "--clock-proof", str(self.clock_path), *extra]

    def run_cli(self, *extra):
        with patch.object(preview_broker_sessions, "OUTPUT_ROOT", self.root):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                result = preview_broker_sessions.main(self.args(*extra))
        return result, output.getvalue()

    def digest(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.db_path, self.schedule_path, self.clock_path)}

    def test_cli_proves_partial_closure_without_changing_official_results_or_files(self):
        from datetime import datetime, timezone
        fixed_now = datetime(2026, 11, 9, 16, tzinfo=timezone.utc)
        # Official report hashes include as_of_utc; compare the same instant.
        clock_patch = patch.object(check_stage0_health, "datetime", wraps=datetime)
        mocked_clock = clock_patch.start()
        self.addCleanup(clock_patch.stop)
        mocked_clock.now.return_value = fixed_now
        before = self.digest()
        official = self.root / "official-before.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check_stage0_health.main(["--state-dir", str(self.root), "--since", "official",
                                                       "--output", str(official)]), 0)
        out = self.root / "preview.json"
        result, text = self.run_cli("--output", str(out))
        self.assertEqual(result, 0)
        report = json.loads(out.read_text())
        self.assertEqual(report["cycle_categories"], {"MISSING_OPEN_QUOTES": 1, "QUOTE_READY_ONLY": 1})
        self.assertEqual(report["since_utc"], observation_ledger.STAGE0_COUNT_SINCE_UTC)
        self.assertEqual(report["schedule_file_sha256"], before["schedule.json"])
        self.assertIn("DIAGNOSTIC_ONLY", text)
        after = self.root / "official-after.json"
        with contextlib.redirect_stdout(io.StringIO()):
            check_stage0_health.main(["--state-dir", str(self.root), "--since", "official", "--output", str(after)])
        a, b = json.loads(official.read_text()), json.loads(after.read_text())
        self.assertEqual(a, b)
        self.assertEqual(self.digest(), before)

    def test_output_rejects_existing_files_and_paths_outside_validation(self):
        existing = self.root / "existing-report.json"
        existing.write_text("preserve", encoding="utf-8")
        result, message = self.run_cli("--output", str(existing))
        self.assertEqual(result, 2)
        self.assertIn("D9_OUTPUT_EXISTS", message)
        self.assertEqual(existing.read_text(encoding="utf-8"), "preserve")
        outside = self.root.parent / (self.root.name + "-outside.json")
        self.assertFalse(outside.exists())
        result, message = self.run_cli("--output", str(outside))
        self.assertEqual(result, 2)
        self.assertIn("D9_OUTPUT_PATH_NOT_ALLOWED", message)
        self.assertFalse(outside.exists())

    def test_missing_clock_validity_and_holiday_scope_stay_unverified(self):
        self.schedule["valid_until_utc"] = None
        self.schedule["verified_broker_dates"] = []
        self.clock["intervals"] = []
        self.write_inputs()
        out = self.root / "preview.json"
        self.assertEqual(self.run_cli("--output", str(out))[0], 0)
        report = json.loads(out.read_text())
        self.assertEqual(report["cycle_categories"], {"UNVERIFIED": 2})
        self.assertNotIn("rate", report)
        self.assertNotIn("verdict", report)

    def test_output_cannot_overwrite_inputs_database_sidecars_or_hardlink_alias(self):
        before = self.digest()
        alias = self.root / "alias.json"
        os.link(self.db_path, alias)
        for path in (self.db_path, self.schedule_path, self.clock_path, alias,
                     Path(str(self.db_path) + "-wal"), Path(str(self.db_path) + "-shm"),
                     Path(str(self.db_path) + "-journal")):
            with self.subTest(path=path):
                result, text = self.run_cli("--output", str(path))
                self.assertEqual(result, 2)
                self.assertIn("D9_OUTPUT_OVERWRITES_INPUT", text)
        self.assertEqual(self.digest(), before)

    def test_malformed_inputs_missing_db_and_future_since_are_blocked(self):
        for payload in ("not json", "[]", '{"schema_version": true}'):
            self.schedule_path.write_text(payload, encoding="utf-8")
            self.assertEqual(self.run_cli()[0], 2)
        self.write_inputs()
        self.assertEqual(self.run_cli("--since", "2099-01-01T00:00:00Z")[0], 2)
        self.assertEqual(self.run_cli("--since", "2026-11-01")[0], 2)
        self.db_path.unlink()
        self.assertEqual(self.run_cli()[0], 2)
        self.assertFalse(self.db_path.exists())

    def test_no_activation_or_historical_override_cli_switch(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            preview_broker_sessions.main(self.args("--effective-utc", "2026-01-01T00:00:00Z"))
        self.assertEqual(error.exception.code, 2)

    def test_observed_example_covers_core_universe_but_authorizes_no_dates(self):
        from katarina.intelligence.operations.broker_sessions import BrokerSessions
        repo = Path(__file__).resolve().parents[2]
        observed = json.loads((repo / "config/broker_sessions.d9.example.json").read_text())
        clock = json.loads((repo / "config/broker_session_clock.d9.example.json").read_text())
        universe = json.loads((repo / "config/observer_universe.json").read_text())
        self.assertEqual(set(observed["symbols"]), set(universe["core"]))
        self.assertIsNone(observed["valid_from_utc"])
        self.assertIsNone(observed["valid_until_utc"])
        self.assertEqual(observed["verified_broker_dates"], [])
        self.assertEqual(clock["intervals"], [])
        policy = BrokerSessions(observed, clock)
        from datetime import datetime
        for symbol in universe["core"]:
            self.assertEqual(policy.classify(datetime.fromisoformat("2026-11-09T22:30:00Z"), symbol,
                                              observed_shift_hours=2)["state"], "UNVERIFIED")
            self.assertIsNone(observed["symbols"][symbol]["quote"]["6"])

    def test_fixture_closes_database_before_temporary_directory_cleanup(self):
        # Keep a strong reference: an open connection must not be left to GC.
        # This reproduces the cause of WinError 32 even on Unix, which permits
        # unlinking an open SQLite file and otherwise conceals the leak.
        real_connect = sqlite3.connect
        connections = []

        def connect(*args, **kwargs):
            db = real_connect(*args, **kwargs)
            connections.append(db)
            return db

        other = type(self)("test_no_activation_or_historical_override_cli_switch")
        try:
            with patch.object(sqlite3, "connect", side_effect=connect):
                other.setUp()
            self.assertEqual(len(connections), 1)
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[0].execute("SELECT 1")
        finally:
            for db in connections:
                db.close()
            other.doCleanups()

    def test_cli_blocks_reduced_or_expanded_schedule_against_canonical_universe(self):
        for change in ("remove", "add"):
            out = self.root / f"scope-{change}.json"
            original = json.loads(json.dumps(self.schedule))
            try:
                if change == "remove":
                    del self.schedule["symbols"]["XAUUSD.vx"]
                else:
                    self.schedule["symbols"]["UNKNOWN.vx"] = self.schedule["symbols"]["EURUSD.vx"]
                self.write_inputs()
                result, text = self.run_cli("--output", str(out))
                self.assertEqual(result, 2)
                self.assertIn("D9_UNIVERSE_MISMATCH", text)
                report = json.loads(out.read_text())
                self.assertEqual(report["required_symbols"], sorted(self.symbols))
                self.assertEqual(report["cycle_categories"], {"UNVERIFIED": 2})
                self.assertEqual(report["universe_file_sha256"],
                                 hashlib.sha256(preview_broker_sessions.UNIVERSE_PATH.read_bytes()).hexdigest())
            finally:
                self.schedule = original

    def test_report_cannot_overwrite_canonical_universe(self):
        # Keep this destructive negative case inside the fixture even if the
        # output guard regresses; never target the checkout's real config.
        canonical_copy = self.root / "canonical-universe.json"
        before = preview_broker_sessions.UNIVERSE_PATH.read_bytes()
        canonical_copy.write_bytes(before)
        with patch.object(preview_broker_sessions, "UNIVERSE_PATH", canonical_copy):
            result, text = self.run_cli("--output", str(canonical_copy))
        self.assertEqual(result, 2)
        self.assertIn("D9_OUTPUT_OVERWRITES_INPUT", text)
        self.assertEqual(canonical_copy.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
