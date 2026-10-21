"""Regression tests for cleanup safeguards (no live filesystem modification)."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.governance.audit_repo_hygiene import audit, audit_tracked_files


class RepoHygieneFilenameTests(unittest.TestCase):
    def test_runtime_health_cannot_be_committed_as_current_source_state(self):
        with TemporaryDirectory() as directory:
            junk, empty = audit_tracked_files(
                Path(directory),
                ["ops/vps/health/primary/status.json", "ops/vps/README.md"],
            )
            self.assertEqual(junk, ["ops/vps/health/primary/status.json"])
            self.assertEqual(empty, [])

    def test_cache_and_editor_junk_are_detected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for rel in ("scripts/__pycache__/module.pyc", "website/page.html.bak", "Thumbs.db", ".env.production"):
                file = root / rel
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("test", encoding="utf-8")
            junk, zero = audit_tracked_files(
                root,
                [
                    "scripts/__pycache__/module.pyc",
                    "website/page.html.bak",
                    "Thumbs.db",
                    ".env.production",
                ],
            )
            self.assertEqual(len(junk), 4)
            self.assertEqual(zero, [])

    def test_empty_executable_script_is_detected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "empty.ps1").touch()
            (root / "__init__.py").touch()
            junk, empty = audit_tracked_files(root, ["empty.ps1", "__init__.py"])
            self.assertEqual(junk, [])
            self.assertEqual(empty, ["empty.ps1"])

    def test_valid_research_and_site_resources_are_preserved(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for rel in (
                "website/brand-logo.base64.txt",
                "docs/validation/experiment.json",
                "src/katarina/intelligence/perception/adaptive_regime.py",
            ):
                file = root / rel
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("active content", encoding="utf-8")
            junk, empty = audit_tracked_files(
                root,
                [
                    "website/brand-logo.base64.txt",
                    "docs/validation/experiment.json",
                    "src/katarina/intelligence/perception/adaptive_regime.py",
                ],
            )
            self.assertEqual((junk, empty), ([], []))

    def test_existing_audit_contract(self):
        with TemporaryDirectory() as directory:
            report = audit(Path(directory))
            self.assertEqual(report["result"], "PASS_REPOSITORY_HYGIENE")
            self.assertFalse(report["live_risk_ready"])
            self.assertEqual(report["accidental_tracked_files"], [])
            self.assertEqual(report["empty_executable_sources"], [])


if __name__ == "__main__":
    unittest.main()
