"""Reason-code traceability tool (cleanup D1): code -> source file:line -> tests."""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("reason_code_index", ROOT / "scripts/governance/reason_code_index.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class ReasonCodeIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = tool.build_index()

    def test_known_p0_clock_code_points_to_source_and_test(self):
        row = self.data["codes"]["CLOCK_BROKER_IDENTITY_MISSING"]
        self.assertEqual(row["severity"], "P0")
        self.assertTrue(any(s.startswith("src/katarina/intelligence/broker/live_clock_probe.py:") for s in row["sites"]))
        self.assertIn("tests/unit/intelligence/test_live_clock_probe.py", row["tests"])

    def test_raise_and_dynamic_prefix_codes_are_indexed(self):
        self.assertIn("BROKER_BAR_CLOCK_NOT_VERIFIED_WP12", self.data["codes"])
        self.assertIn("UNAVAILABLE_*", self.data["codes"])  # 'UNAVAILABLE_' + type(exc).__name__
        family = self.data["codes"]["SHADOW_EVALUATION_FAILED_*"]
        self.assertTrue(any(s.startswith("src/katarina/intelligence/cognition/observer.py:") for s in family["sites"]))

    def test_protocol_codes_are_frozen_and_listed(self):
        self.assertEqual(self.data["protocol"]["1"], "MALFORMED_FRAME")
        self.assertIn("never redefined", self.data["protocol_rule"])

    def test_find_reports_unknown_code_as_not_found(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(tool.main(["--find", "NO_SUCH_KATARINA_CODE_X"]), 1)
        self.assertEqual(json.loads(out.getvalue())["status"], "REASON_CODE_NOT_FOUND")

    def test_committed_index_documents_the_lookup_command(self):
        text = (ROOT / "docs/maintenance/REASON_CODE_INDEX.md").read_text(encoding="utf-8")
        self.assertIn("reason_code_index.py --find", text)
        self.assertIn("`CLOCK_BROKER_IDENTITY_MISSING`", text)


if __name__ == "__main__":
    unittest.main()
