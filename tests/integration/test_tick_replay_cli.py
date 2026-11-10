"""Loader + CLI integration for the tick-replay simulator (synthetic fixture, technical only).

Covers: manifest/hash contract, fail-closed rejections, the Owner-approval gate (no replay without it) and a
reproducible end-to-end replay whose ledger hash is identical across runs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tests.unit.research._tick_replay_fixtures import B1_SWEEP_START, DAY0, MIN, SHA, b1_path  # noqa: E402

CLI = ROOT / "scripts" / "research" / "replay_six_candidates.py"


def write_inputs(folder: Path, ticks, *, tamper=None, drop_sessions=False):
    tick_file = folder / "ticks.csv"
    with tick_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_msc", "bid", "ask", "flags"])
        for t in ticks:
            writer.writerow([t.time_ms, f"{t.bid / 100:.2f}", f"{t.ask / 100:.2f}", 6])
    digest = hashlib.sha256(tick_file.read_bytes()).hexdigest()
    week = [DAY0, DAY0 + 7 * 86_400_000]
    manifest = {
        "dataset": {"symbol": "XAUUSD.vx", "server": "fixture", "tick_file_sha256": digest,
                    "clock_evidence_sha256": SHA, "sequence_evidence": "UNVERIFIED", "max_quote_gap_ms": 30 * MIN},
        "symbol_contract": {"symbol": "XAUUSD.vx", "digits": 2, "point": 0.01, "tick_size": 0.01,
                            "stops_level_points": 31, "freeze_level_points": 0, "contract_size": 100.0,
                            "evidence_sha256": SHA},
        "sessions": {"quote": [week], "trade": [week], "source": "fixture", "evidence_sha256": SHA},
        "costs": {"currency": "USD", "commission_per_lot_round_trip": 7.0, "swap_long_per_lot_night": -30.0,
                  "swap_short_per_lot_night": 10.0, "rollover_utc_minute": 1260, "triple_swap_weekday": 2,
                  "evidence_sha256": SHA},
    }
    if drop_sessions:
        manifest.pop("sessions")
    if tamper:
        tamper(manifest)
    manifest_file = folder / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    return tick_file, manifest_file


def cli(*args):
    proc = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True, timeout=120)
    return proc.returncode, json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else proc.stderr


class TickReplayCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.ticks = b1_path().at(B1_SWEEP_START + 6 * MIN, 1550).ticks()

    def tearDown(self):
        self.tmp.cleanup()

    def test_without_owner_approval_only_validates(self):
        ticks, manifest = write_inputs(self.dir, self.ticks)
        code, out = cli("--ticks", ticks, "--manifest", manifest)
        self.assertEqual(0, code)
        self.assertEqual("INPUT_VALID", out["status"])
        self.assertEqual("NOT_RUN_OWNER_APPROVAL_REQUIRED", out["replay"])
        self.assertEqual(len(self.ticks), out["ticks"])

    def test_rejections_fail_closed(self):
        cases = {
            "TICK_FILE_HASH_MISMATCH": lambda m: m["dataset"].update(tick_file_sha256="0" * 64),
            "CLOCK_EVIDENCE_MISSING": lambda m: m["dataset"].update(clock_evidence_sha256=""),
            "SYMBOL_CONTRACT_EVIDENCE_MISSING": lambda m: m["symbol_contract"].update(evidence_sha256="x"),
            "COST_EVIDENCE_MISSING": lambda m: m["costs"].update(evidence_sha256=""),
            "MANIFEST_INCOMPLETE": lambda m: m.pop("costs"),
        }
        for reason, tamper in cases.items():
            with self.subTest(reason=reason):
                folder = self.dir / reason
                folder.mkdir()
                ticks, manifest = write_inputs(folder, self.ticks, tamper=tamper)
                code, out = cli("--ticks", ticks, "--manifest", manifest)
                self.assertEqual(2, code)
                self.assertEqual(reason, out["reason_code"])

    def test_off_grid_price_is_rejected(self):
        ticks, manifest = write_inputs(self.dir, self.ticks)
        rows = ticks.read_text(encoding="utf-8").splitlines()
        rows[3] = rows[3].replace(rows[3].split(",")[1], rows[3].split(",")[1] + "5", 1)
        ticks.write_text("\n".join(rows) + "\n", encoding="utf-8")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["dataset"]["tick_file_sha256"] = hashlib.sha256(ticks.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(data), encoding="utf-8")
        code, out = cli("--ticks", ticks, "--manifest", manifest)
        self.assertEqual((2, "PRICE_OFF_TICK_GRID"), (code, out["reason_code"]))

    def test_approved_replay_is_reproducible_and_reports_no_profit_metrics(self):
        ticks, manifest = write_inputs(self.dir, self.ticks)
        hashes = []
        for run in ("a", "b"):
            out_dir = self.dir / run
            code, out = cli("--ticks", ticks, "--manifest", manifest, "--output-dir", out_dir,
                            "--owner-approval-ref", "fixture-test-only")
            self.assertEqual((0, "RUN"), (code, out["replay"]))
            hashes.append(out["ledger_sha256"])
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(0, summary["orders_sent"])
            self.assertNotIn("trades", json.dumps(summary["event_counts"]))
            ledger = (out_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(summary["event_count"], len(ledger))
        self.assertEqual(hashes[0], hashes[1])

    def test_missing_sessions_still_loads_but_blocks_entries(self):
        ticks, manifest = write_inputs(self.dir, self.ticks, drop_sessions=True)
        code, out = cli("--ticks", ticks, "--manifest", manifest, "--output-dir", self.dir / "o",
                        "--owner-approval-ref", "fixture-test-only")
        self.assertEqual(0, code)
        summary = json.loads((self.dir / "o" / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(1, summary["event_counts"]["B1"].get("ENTRY_BLOCKED:BLOCKED_SESSION_EVIDENCE"))


if __name__ == "__main__":
    unittest.main()
