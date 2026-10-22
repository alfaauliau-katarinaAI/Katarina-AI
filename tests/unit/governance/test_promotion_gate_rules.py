"""Promotion records must carry validation PASS + Owner approval; tampering is detected."""
import json
import tempfile
import unittest
from pathlib import Path

from katarina.governance.promotion_gate import (
    LOCK_PATH, RECORD_DIR, check, file_sha256, record_problems, write_lock)


class PromotionGateRuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "config").mkdir()
        (self.root / RECORD_DIR).mkdir(parents=True)
        (self.root / "strategy.py").write_text("THRESHOLD = 0.62\n")

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, name, **fields):
        rec = {"id": "P-0001", "kind": "PROMOTION",
               "owner_approval": {"approved_by": "owner", "date": "2026-10-22"},
               "files": {"strategy.py": file_sha256(self.root / "strategy.py")}}
        rec.update(fields)
        rel = f"{RECORD_DIR}/{name}.json"
        (self.root / rel).write_text(json.dumps(rec))
        return rel, rec

    def passing_report(self):
        report = self.root / "report.json"
        report.write_text('{"result": "PASS"}')
        return {"status": "PASS", "report": "report.json", "report_sha256": file_sha256(report)}

    def test_promotion_requires_pass_report_and_owner(self):
        rel, rec = self.record("a")
        problems = record_problems(self.root, rec, rel)
        self.assertIn("validation_not_pass", problems)
        self.assertIn("validation_report_missing", problems)
        _, rec = self.record("b", validation=self.passing_report(), owner_approval={})
        self.assertIn("owner_approval_missing", record_problems(self.root, rec, rel))

    def test_valid_promotion_locks_and_detects_later_edits(self):
        rel, _ = self.record("ok", validation=self.passing_report())
        write_lock(self.root, rel)
        self.assertEqual(check(self.root), [])
        (self.root / "strategy.py").write_text("THRESHOLD = 0.50\n")
        self.assertTrue(any("strategy.py" in v for v in check(self.root)))

    def test_tampered_report_or_crlf(self):
        rel, rec = self.record("ok", validation=self.passing_report())
        (self.root / "report.json").write_text('{"result": "FAIL"}')
        self.assertIn("validation_report_hash_mismatch", record_problems(self.root, rec, rel))
        (self.root / "strategy.py").write_bytes(b"THRESHOLD = 0.62\r\n")
        self.assertEqual(file_sha256(self.root / "strategy.py"),
                         rec["files"]["strategy.py"])

    def test_baseline_kind_only_for_p0000_and_lock_needs_matching_record(self):
        rel, rec = self.record("base", kind="BASELINE_PRE_GATE")
        self.assertIn("baseline_only_allowed_as_P-0000", record_problems(self.root, rec, rel))
        rel, _ = self.record("ok", validation=self.passing_report())
        write_lock(self.root, rel)
        lock = json.loads((self.root / LOCK_PATH).read_text())
        lock["files"]["strategy.py"] = "0" * 64
        (self.root / LOCK_PATH).write_text(json.dumps(lock))
        self.assertTrue(any("daftar hash" in v for v in check(self.root)))


if __name__ == "__main__":
    unittest.main()
