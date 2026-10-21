from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
COMMAND = ROOT / "scripts" / "ai" / "validate_brain.py"


class AIBrainPipelineIntegrationTests(unittest.TestCase):
    def run_cli(self, rows: list[dict], *, feature_names="technical,macro"):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        input_file = Path(temp.name) / "trade-outcomes.jsonl"
        output_file = Path(temp.name) / "evidence.json"
        input_file.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(
            [sys.executable, str(COMMAND), "--input", str(input_file),
             "--features", feature_names, "--output", str(output_file)],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False,
        )
        payload = json.loads(output_file.read_text(encoding="utf-8")) if output_file.exists() else None
        return proc, payload

    @staticmethod
    def synthetic_rows(count=70):
        return [{
            "sample_id": f"synthetic-{i}", "observed_ns": (i + 1) * 1000,
            "label_known_ns": (i + 1) * 1000 + 200,
            "features": [1.0 if i % 2 else -1.0, .3 if i % 2 else .1],
            "profitable_after_costs": i % 2,
        } for i in range(count)]

    def test_offline_training_report_never_grants_live_authority(self):
        proc, payload = self.run_cli(self.synthetic_rows())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["result"], "PASS_AI_BRAIN_RESEARCH_CANDIDATE")
        self.assertFalse(payload["data_provenance_verified"])
        self.assertTrue(payload["research_only"])
        self.assertFalse(payload["live_execution_enabled"])
        self.assertFalse(payload["live_risk_ready"])
        self.assertTrue(payload["model"]["research_only"])
        self.assertGreater(len(payload["model_hash"]), 10)

    def test_too_few_realized_trades_fails_without_model(self):
        proc, payload = self.run_cli(self.synthetic_rows(5))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertFalse(payload["validated"])
        self.assertIsNone(payload["model"])
        self.assertFalse(payload["live_execution_enabled"])

    def test_corrupt_jsonl_is_rejected_before_evidence(self):
        rows = self.synthetic_rows()
        rows[0]["label_known_ns"] = 0
        proc, payload = self.run_cli(rows)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(payload)
        self.assertIn("invalid record at line 1", proc.stderr)

    def test_no_leakage_from_holdout_labels_before_training(self):
        rows = self.synthetic_rows()
        rows[2]["label_known_ns"] = 110_000
        proc, payload = self.run_cli(rows)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(payload["train_count"], 55)
        self.assertLess(payload["trained_until_ns"], payload["cutoff_ns"])


if __name__ == "__main__":
    unittest.main()
