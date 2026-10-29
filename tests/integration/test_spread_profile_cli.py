"""Integration test for spread_profile CLI script (docs/ROADMAP.md WP10a)."""
from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class SpreadProfileCLIIntegrationTests(unittest.TestCase):
    def test_cli_execution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            state_dir = tmp_path / "state"
            state_dir.mkdir()

            tick_file = state_dir / "broker-ticks" / "EURUSD" / "2026-10-22.csv.gz"
            tick_file.parent.mkdir(parents=True, exist_ok=True)

            lines = [
                "time_msc,bid,ask,flags",
                "1792627200000,1.10000,1.10020,0",
                "1792627230000,1.10000,1.10030,0",
            ]
            decompressed = ("\n".join(lines) + "\n").encode("ascii")
            digest = hashlib.sha256(decompressed).hexdigest()

            with gzip.GzipFile(filename=str(tick_file), mode="wb", mtime=0) as gz:
                gz.write(decompressed)

            db_path = state_dir / "context.sqlite3"
            with contextlib.closing(sqlite3.connect(db_path)) as db:
                db.execute("CREATE TABLE broker_tick_days(symbol TEXT, day TEXT, status TEXT, sha256 TEXT, file TEXT, server_shift_hours INTEGER DEFAULT 2)")
                db.execute("INSERT INTO broker_tick_days(symbol, day, status, sha256, file) VALUES('EURUSD', '2026-10-22', 'STORED', ?, ?)",
                           (digest, "broker-ticks/EURUSD/2026-10-22.csv.gz"))
                db.commit()

            output_file = tmp_path / "build" / "spread_profile.json"
            script = REPO_ROOT / "scripts" / "research" / "spread_profile.py"

            cmd = [
                sys.executable, str(script),
                "--state-dir", str(state_dir),
                "--since", "2026-10-22",
                "--until", "2026-10-22",
                "--output", str(output_file),
            ]

            env = {"PYTHONPATH": str(REPO_ROOT / "src")}
            res = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True, text=True)

            self.assertEqual(res.returncode, 0, f"CLI stderr: {res.stderr}")
            self.assertTrue(output_file.exists())

            report = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(report["usage"], "DESCRIPTIVE_ONLY_NOT_FOR_TUNING")
            self.assertEqual(report["label"], "DESKRIPTIF — data forward, bukan untuk penyetelan")
            self.assertIn("EURUSD", report["symbols"])


if __name__ == "__main__":
    unittest.main()
