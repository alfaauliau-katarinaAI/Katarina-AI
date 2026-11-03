"""Tests for WP14 read-only, deterministic data evidence auditor."""
import contextlib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from katarina.intelligence.operations import data_health, observation_ledger
from scripts.ai import check_stage0_health


class TestDataAuditWP14(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "context.sqlite3"
        # Create schema and initial baseline
        with self._writable_db() as db:
            observation_ledger.setup(db)

    @contextlib.contextmanager
    def _writable_db(self):
        # A sqlite3.Connection context manager commits but DOES NOT close.
        # Windows keeps context.sqlite3 locked if connections are not closed.
        with contextlib.closing(sqlite3.connect(self.db_path)) as db:
            with db:
                yield db

    def tearDown(self):
        self.temp_dir.cleanup()

    def _file_sha256(self, path: Path) -> str:
        with open(path, "rb") as f:
            return hashlib.file_digest(f, "sha256").hexdigest()

    def test_mixed_pass_and_no_data_never_passes_audit(self):
        """Partial required evidence cannot be promoted by an unrelated PASS."""
        verdict = data_health._wp14_audit_verdict
        self.assertEqual(verdict([{"status": "PASS"}, {"status": "NO_DATA"}]),
                         "IN_PROGRESS")
        self.assertEqual(verdict([{"status": "BLOCKED"}, {"status": "PASS"}]),
                         "BLOCKED")
        self.assertEqual(verdict([{"status": "NO_DATA"}]), "NO_DATA")
        self.assertEqual(verdict([{"status": "PASS"}, {"status": "PASS"}]),
                         "PASS")
        now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as db:
            db.execute("PRAGMA query_only = ON")
            report = data_health.audit(db, now)
        self.assertEqual(report["verdict"], "NO_DATA")

    def test_database_sha256_unmodified_proof_of_read_only(self):
        """Proof of zero DB write: context.sqlite3 SHA256 remains byte-identical before and after audit."""
        now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
        # Populate dummy cycle so DB has content
        with self._writable_db() as db:
            cid = observation_ledger.record_snapshot(
                db,
                observed_utc=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
                clock_shift_hours=2,
                cards={"EURUSD.vx": {}},
                quotes={"EURUSD.vx": (1.0500, 1.0502, datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc).timestamp())},
            )
            observation_ledger.close_cycle(
                db,
                finished_utc=datetime(2026, 11, 2, 10, 0, 5, tzinfo=timezone.utc),
                cycle_id=cid,
                status="OK",
            )
            observation_ledger.record_decision_shadow(
                db, cid, symbol="EURUSD.vx", mode="legacy_fail_closed",
                action="WAIT", conditional_side="WAIT", blockers=["TEST_BLOCKER"],
            )
            observation_ledger.record_decision_shadow(
                db, cid, symbol="EURUSD.vx", mode="measured_inputs",
                action="WAIT", conditional_side="WAIT", blockers=["TEST_BLOCKER"],
            )

        sha_before = self._file_sha256(self.db_path)

        # Open in mode=ro and PRAGMA query_only=ON
        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=10)) as ro_db:
            ro_db.execute("PRAGMA query_only = ON")
            report = data_health.audit(ro_db, now)

        sha_after = self._file_sha256(self.db_path)
        self.assertEqual(sha_before, sha_after, "Database file modified during read-only audit!")
        self.assertIn("report_sha256", report)

    def test_deterministic_output(self):
        """Identical inputs and DB produce byte-identical reports and matching report_sha256."""
        now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
        with self._writable_db() as db:
            cid = observation_ledger.record_snapshot(
                db,
                observed_utc=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
                clock_shift_hours=2,
                cards={"EURUSD.vx": {}},
                quotes={"EURUSD.vx": (1.0500, 1.0502, datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc).timestamp())},
            )
            observation_ledger.close_cycle(
                db,
                finished_utc=datetime(2026, 11, 2, 10, 0, 5, tzinfo=timezone.utc),
                cycle_id=cid,
                status="OK",
            )

        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as ro_db:
            ro_db.execute("PRAGMA query_only = ON")
            rep1 = data_health.audit(ro_db, now)
            rep2 = data_health.audit(ro_db, now)

        rep1_json = json.dumps(rep1, sort_keys=True, separators=(",", ":"))
        rep2_json = json.dumps(rep2, sort_keys=True, separators=(",", ":"))
        self.assertEqual(rep1_json, rep2_json)
        self.assertEqual(rep1["report_sha256"], rep2["report_sha256"])

    def test_missing_quote_and_negative_spread(self):
        """Detect missing quotes and negative spreads; marks symbols restricted or quarantined."""
        now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
        with self._writable_db() as db:
            # Cycle 1: quote missing (sensor failure)
            cid1 = observation_ledger.record_snapshot(
                db,
                observed_utc=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
                clock_shift_hours=2,
                cards={"GBPUSD.vx": {"sensor_reason": "DISCONNECTED"}},
                quotes={},
            )
            observation_ledger.close_cycle(
                db,
                finished_utc=datetime(2026, 11, 2, 10, 0, 5, tzinfo=timezone.utc),
                cycle_id=cid1,
                status="OK",
            )
            # Cycle 2: negative spread (ask < bid)
            cid2 = "c-20261102T100100.000000Z"
            db.execute(
                "INSERT INTO observer_cycles(cycle_id, observed_utc, status, clock_shift_hours) "
                "VALUES(?,?,?,?)",
                (cid2, "2026-11-02T10:01:00+00:00", "OK", 2),
            )
            db.execute(
                "INSERT INTO observer_quotes(cycle_id, symbol, observed_utc, tick_epoch, bid, ask, spread, status) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (cid2, "XAUUSD.vx", "2026-11-02T10:01:00+00:00", 1762077660.0, 2700.0, 2690.0, -10.0, "OK"),
            )

        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as ro_db:
            ro_db.execute("PRAGMA query_only = ON")
            report = data_health.audit(ro_db, now)

        self.assertEqual(report["verdict"], "BLOCKED")
        checks = {f["check"]: f for f in report["findings"]}
        self.assertIn("quote_spread_non_negative", checks)
        self.assertEqual(checks["quote_spread_non_negative"]["status"], "BLOCKED")
        self.assertIn("NEGATIVE_SPREAD", checks["quote_spread_non_negative"]["reason"])

        self.assertEqual(report["symbol_day_summary"].get("XAUUSD.vx:2026-11-02"), "karantina")
        self.assertEqual(report["symbol_day_summary"].get("GBPUSD.vx:2026-11-02"), "terbatas")

    def test_mixed_clock_shift_offsets_per_day(self):
        """Mixed clock shifts in a single day (except NO_MARKET_DATA) triggers BLOCKED and quarantine."""
        now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
        with self._writable_db() as db:
            # Two cycles on 2026-11-02 with different shift hours (e.g., 2 and 3)
            cid1 = "c-1"
            cid2 = "c-2"
            db.execute(
                "INSERT INTO observer_cycles(cycle_id, observed_utc, status, clock_shift_hours) "
                "VALUES(?,?,?,?)",
                (cid1, "2026-11-02T02:00:00+00:00", "OK", 2),
            )
            db.execute(
                "INSERT INTO observer_cycles(cycle_id, observed_utc, status, clock_shift_hours) "
                "VALUES(?,?,?,?)",
                (cid2, "2026-11-02T04:00:00+00:00", "OK", 3),
            )
            db.execute(
                "INSERT INTO observer_quotes(cycle_id, symbol, observed_utc, tick_epoch, bid, ask, spread, status) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (cid1, "EURUSD.vx", "2026-11-02T02:00:00+00:00", 1762048800.0, 1.05, 1.0501, 0.0001, "OK"),
            )

        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as ro_db:
            ro_db.execute("PRAGMA query_only = ON")
            report = data_health.audit(ro_db, now)

        findings = [f for f in report["findings"] if f["check"] == "daily_clock_shift_uniform"]
        self.assertTrue(any(f["status"] == "BLOCKED" and "MIXED_DAILY_CLOCK_SHIFTS" in f["reason"] for f in findings))
        self.assertEqual(report["symbol_day_summary"].get("EURUSD.vx:2026-11-02"), "karantina")

    def test_tick_day_hash_mismatch_and_reconciliation(self):
        """Tick day file SHA-256 mismatch against disk file and snapshot reconciliation failure."""
        now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
        tick_file = Path(self.temp_dir.name) / "ticks.csv.gz"
        tick_file.write_bytes(b"corrupted_tick_data")

        with self._writable_db() as db:
            db.execute(
                "INSERT INTO broker_tick_days(symbol, day, status, sha256, file, snapshots_checked, snapshots_matched, server_shift_hours) "
                "VALUES(?,?,?,?,?,?,?,?)",
                ("EURUSD.vx", "2026-10-30", "STORED", "expected_different_sha256_hash", str(tick_file), 100, 95, 2),
            )

        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as ro_db:
            ro_db.execute("PRAGMA query_only = ON")
            report = data_health.audit(ro_db, now)

        checks = {f["check"]: f for f in report["findings"]}
        self.assertEqual(checks["tick_file_hash"]["status"], "BLOCKED")
        self.assertIn("TICK_FILE_HASH_MISMATCH", checks["tick_file_hash"]["reason"])
        self.assertEqual(checks["tick_snapshot_reconciliation"]["status"], "BLOCKED")
        self.assertIn("RECONCILIATION_MISMATCH", checks["tick_snapshot_reconciliation"]["reason"])
        self.assertEqual(report["symbol_day_summary"].get("EURUSD.vx:2026-10-30"), "karantina")

    def _audit_relative_tick_file(self, content: bytes, recorded_sha: str | None, state_dir):
        now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
        rel = Path("broker-ticks") / "EURUSD.vx" / "2026-10-30.csv.gz"
        target = Path(self.temp_dir.name) / rel
        target.parent.mkdir(parents=True)
        target.write_bytes(content)
        with self._writable_db() as db:
            db.execute(
                "INSERT INTO broker_tick_days(symbol, day, status, sha256, file, snapshots_checked, "
                "snapshots_matched, server_shift_hours) VALUES(?,?,?,?,?,?,?,?)",
                ("EURUSD.vx", "2026-10-30", "STORED", recorded_sha, rel.as_posix(), 10, 10, 2),
            )
        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as ro_db:
            ro_db.execute("PRAGMA query_only = ON")
            report = data_health.audit(ro_db, now, state_dir=state_dir)
        return {f["check"]: f for f in report["findings"]}

    def test_ledger_relative_tick_file_is_resolved_against_state_dir(self):
        """The ledger stores 'broker-ticks/...' relative to the state dir, not to the CWD."""
        content = b"tick-archive"
        checks = self._audit_relative_tick_file(
            content, hashlib.sha256(content).hexdigest(), self.temp_dir.name)
        self.assertEqual(checks["tick_file_hash"]["status"], "PASS")

    def test_stored_tick_file_without_recorded_hash_is_blocked(self):
        checks = self._audit_relative_tick_file(b"tick-archive", None, self.temp_dir.name)
        self.assertEqual(checks["tick_file_hash"]["status"], "BLOCKED")
        self.assertEqual(checks["tick_file_hash"]["reason"], "TICK_FILE_HASH_NOT_RECORDED")

    def test_cli_audit_passes_state_dir_for_relative_tick_files(self):
        content = b"tick-archive"
        self._audit_relative_tick_file(content, hashlib.sha256(content).hexdigest(), None)
        out = Path(self.temp_dir.name) / "audit.json"
        check_stage0_health.main(["--state-dir", self.temp_dir.name, "--audit", "--output", str(out)])
        findings = json.loads(out.read_text(encoding="utf-8"))["findings"]
        statuses = {f["status"] for f in findings if f["check"] == "tick_file_hash"}
        self.assertEqual(statuses, {"PASS"})

    def test_decision_shadow_completeness(self):
        """Incomplete decision_shadow modes per cycle x symbol triggers BLOCKED."""
        now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
        with self._writable_db() as db:
            cid = observation_ledger.record_snapshot(
                db,
                observed_utc=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
                clock_shift_hours=2,
                cards={"EURUSD.vx": {}},
                quotes={"EURUSD.vx": (1.0500, 1.0502, datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc).timestamp())},
            )
            observation_ledger.close_cycle(
                db,
                finished_utc=datetime(2026, 11, 2, 10, 0, 5, tzinfo=timezone.utc),
                cycle_id=cid,
                status="OK",
            )
            # Only record legacy_fail_closed, measured_inputs missing
            observation_ledger.record_decision_shadow(
                db, cid, symbol="EURUSD.vx", mode="legacy_fail_closed",
                action="WAIT", conditional_side="WAIT", blockers=["TEST_BLOCKER"],
            )

        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as ro_db:
            ro_db.execute("PRAGMA query_only = ON")
            report = data_health.audit(ro_db, now)

        checks = [f for f in report["findings"] if f["check"] == "decision_shadow_completeness"]
        self.assertTrue(any(f["status"] == "BLOCKED" and "measured_inputs" in f["reason"] for f in checks))

    def test_dev_dataset_manifest_and_clock_evidence(self):
        """Audit WP8a dataset manifest: file hash and clock_evidence verification."""
        dataset_dir = Path(self.temp_dir.name) / "dev_dataset"
        dataset_dir.mkdir()
        sym_dir = dataset_dir / "EURUSD"
        sym_dir.mkdir()
        csv_file = sym_dir / "M5.csv.gz"
        csv_file.write_bytes(b"content")
        csv_sha = hashlib.sha256(b"content").hexdigest()

        # Build valid manifest
        manifest_data = {
            "schema_version": 1,
            "stage": "WP8A_DEVELOPMENT_ONLY",
            "files": {
                "EURUSD/M5.csv.gz": {
                    "symbol": "EURUSD",
                    "timeframe": "M5",
                    "sha256": csv_sha,
                    "clock_evidence": [
                        {
                            "start_utc": "2026-10-01T00:00:00+00:00",
                            "end_utc": "2026-10-08T00:00:00+00:00",
                            "shift_hours": 2,
                            "time_basis": "INDEPENDENT_UTC",
                            "source_sha256": "a" * 64,
                        }
                    ],
                }
            },
        }
        canonical_body = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        manifest_data["manifest_sha256"] = hashlib.sha256(canonical_body.encode("utf-8")).hexdigest()
        (dataset_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

        now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as ro_db:
            ro_db.execute("PRAGMA query_only = ON")
            report = data_health.audit(ro_db, now, dataset_dir=str(dataset_dir))

        checks = {f["check"]: f for f in report["findings"] if f["check"].startswith("dataset_")}
        self.assertEqual(checks["dataset_manifest_hash"]["status"], "PASS")
        self.assertEqual(checks["dataset_file_hash"]["status"], "PASS")
        self.assertEqual(checks["dataset_clock_evidence"]["status"], "PASS")

        # Now tamper with clock_evidence: remove clock_evidence
        manifest_data["files"]["EURUSD/M5.csv.gz"]["clock_evidence"] = []
        body_tampered = {k: v for k, v in manifest_data.items() if k != "manifest_sha256"}
        canonical_tampered = json.dumps(body_tampered, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        manifest_data["manifest_sha256"] = hashlib.sha256(canonical_tampered.encode("utf-8")).hexdigest()
        (dataset_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

        with contextlib.closing(sqlite3.connect(uri, uri=True)) as ro_db:
            ro_db.execute("PRAGMA query_only = ON")
            tampered_report = data_health.audit(ro_db, now, dataset_dir=str(dataset_dir))

        tampered_checks = {f["check"]: f for f in tampered_report["findings"] if f["check"].startswith("dataset_")}
        self.assertEqual(tampered_checks["dataset_clock_evidence"]["status"], "BLOCKED")
        self.assertIn("CLOCK_EVIDENCE_MISSING", tampered_checks["dataset_clock_evidence"]["reason"])

    def test_cli_check_stage0_health_audit(self):
        """CLI check_stage0_health.py --audit --since ISO --output JSON executes cleanly."""
        out_path = Path(self.temp_dir.name) / "audit_report.json"
        state_dir = self.temp_dir.name
        argv = [
            "--state-dir", state_dir,
            "--audit",
            "--since", "2026-10-01T00:00:00+00:00",
            "--output", str(out_path),
        ]
        ret = check_stage0_health.main(argv)
        self.assertEqual(ret, 0)
        self.assertTrue(out_path.is_file())
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["stage"], "WP14_DATA_EVIDENCE_AUDIT")
        self.assertIn("report_sha256", saved)
        self.assertIn("findings", saved)


if __name__ == "__main__":
    unittest.main()
