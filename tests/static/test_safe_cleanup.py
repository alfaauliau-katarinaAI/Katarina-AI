"""safe_cleanup acceptance (AUTO_CLEANUP_CODING_GATE.md section C/E) on a throwaway git repo."""
from contextlib import redirect_stdout
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("safe_cleanup", ROOT / "scripts/governance/safe_cleanup.py")
cleanup = importlib.util.module_from_spec(spec)
sys.modules["safe_cleanup"] = cleanup
spec.loader.exec_module(cleanup)
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@test.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@test.invalid"}


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                   env=dict(os.environ, **GIT_ENV))


def snapshot(root: Path) -> dict:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink():
                out[path.relative_to(root).as_posix()] = "LINK"
            else:
                out[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class SafeCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root = base / "repo"
        self.outside = base / "outside"
        self.outside.mkdir()
        (self.outside / "precious.txt").write_text("outside the worktree", encoding="utf-8")
        files = {
            "src/pkg/__init__.py": "",
            "src/pkg/core.py": "VALUE = 1\n" * 10,
            "tests/test_core.py": "import unittest\n" * 5,
            "docs/governance/owner.md": "owner doc\n",
        }
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        git(self.root, "init", "-q", "-b", "dev")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "init")
        # Generated artifacts that may go:
        self.junk = ["src/pkg/__pycache__/core.cpython-312.pyc", "tests/__pycache__/t.cpython-312.pyc",
                     ".pytest_cache/v/cache/nodeids", "src/pkg/editor.py~", "build/validation/report.json"]
        for rel in self.junk:
            self._write(rel, "generated")
        # Things that must never go, even though they look like caches:
        self.protected = ["state/__pycache__/x.pyc", "backups/__pycache__/x.pyc", "private/__pycache__/x.pyc",
                          "logs/__pycache__/x.pyc", "build/body/context.sqlite3", "build/body/context.sqlite3-wal",
                          "build/code-gate/failure-ledger.json", "docs/governance/draft~", "state/context.sqlite3",
                          "build/stage10/broker-ticks/2026-11-03.csv.gz"]
        for rel in self.protected:
            self._write(rel, "protected")
        # A tracked .pyc (somebody force-added it): source of truth is Git, never deleted.
        self._write("src/pkg/tracked.pyc", "tracked")
        git(self.root, "add", "-f", "src/pkg/tracked.pyc")
        git(self.root, "commit", "-q", "-m", "tracked pyc")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_check_and_dry_run_change_nothing(self):
        before = snapshot(self.root)
        report = cleanup.plan(self.root)
        self.assertEqual(snapshot(self.root), before)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cleanup.main(["--dry-run", "--repo-root", str(self.root)]), 0)
            self.assertEqual(cleanup.main(["--check", "--repo-root", str(self.root)]), 0)
        self.assertEqual(snapshot(self.root), before)
        planned = {item["path"] for item in report["artifacts"]}
        self.assertTrue({"src/pkg/__pycache__", "tests/__pycache__", ".pytest_cache", "src/pkg/editor.py~",
                         "build/validation"} <= planned)
        self.assertEqual(report["summary"]["tracked_source_deleted"], 0)

    def test_apply_safe_deletes_only_allowlisted_untracked_artifacts_and_is_idempotent(self):
        report = cleanup.apply_safe(self.root)
        for rel in self.junk:
            self.assertFalse((self.root / rel).exists(), rel)
        for rel in self.protected + ["src/pkg/tracked.pyc", "src/pkg/core.py", "docs/governance/owner.md"]:
            self.assertTrue((self.root / rel).exists(), rel)
        refused = {item["path"]: item["reason"] for item in report["refused"]}
        self.assertEqual(refused["state/__pycache__"], "PROTECTED_LOCATION")
        self.assertEqual(refused["build/body"], "PROTECTED_CONTENT")  # sqlite + WAL inside a report folder
        self.assertEqual(refused["src/pkg/tracked.pyc"], "TRACKED_BY_GIT")
        self.assertEqual(refused["docs/governance/draft~"], "PROTECTED_LOCATION")
        self.assertEqual(refused["build/stage10"], "PROTECTED_CONTENT")  # tick archive
        self.assertNotIn("build/code-gate", {i["path"] for i in report["artifacts"] + report["refused"]})
        audit = (self.root / "build/code-gate/cleanup-audit.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(audit), 1)
        before = snapshot(self.root)
        second = cleanup.apply_safe(self.root)  # idempotent
        self.assertEqual(second["summary"]["deleted"], 0)
        after = snapshot(self.root)
        after.pop("build/code-gate/cleanup-audit.jsonl")
        before.pop("build/code-gate/cleanup-audit.jsonl")
        self.assertEqual(after, before)

    def test_symlink_or_junction_to_outside_is_refused_and_target_survives(self):
        link = self.root / "src" / "__pycache__"
        try:
            os.symlink(self.outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks need privileges on this host")
        nested = self.root / "build" / "validation" / "escape"
        nested.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(self.outside, nested, target_is_directory=True)
        report = cleanup.apply_safe(self.root)
        refused = {item["path"]: item["reason"] for item in report["refused"]}
        self.assertEqual(refused["src/__pycache__"], "SYMLINK_OR_JUNCTION")
        self.assertEqual(refused["build/validation"], "SYMLINK_OR_JUNCTION")
        self.assertEqual((self.outside / "precious.txt").read_text(encoding="utf-8"), "outside the worktree")

    def test_path_escape_is_refused(self):
        with self.assertRaises(cleanup.Refused) as error:
            cleanup.guard(self.root, "../outside/precious.txt", set())
        self.assertEqual(str(error.exception), "PATH_ESCAPE")
        with self.assertRaises(cleanup.Refused):
            cleanup.guard(self.root, str(self.outside / "precious.txt"), set())

    def test_apply_refuses_main_production_and_a_changing_worktree(self):
        git(self.root, "checkout", "-q", "-b", "main")
        with self.assertRaisesRegex(cleanup.Refused, "MAIN_BRANCH"):
            cleanup.apply_safe(self.root)
        git(self.root, "checkout", "-q", "dev")
        (self.root / ".katarina-production").write_text("", encoding="utf-8")
        with self.assertRaisesRegex(cleanup.Refused, "PRODUCTION_CHECKOUT"):
            cleanup.apply_safe(self.root)
        (self.root / ".katarina-production").unlink()
        fingerprints = iter(["planned", "changed"])
        with patch.object(cleanup, "_fingerprint", side_effect=lambda root: next(fingerprints)):
            with self.assertRaisesRegex(cleanup.Refused, "WORKTREE_CHANGED_DURING_CLEANUP"):
                cleanup.apply_safe(self.root)
        self.assertTrue((self.root / "src/pkg/__pycache__/core.cpython-312.pyc").exists())
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cleanup.main(["--apply-safe", "--repo-root", str(self.root / "..")]), 2)
        self.assertIn("NOT_A_GIT_WORKTREE_ROOT", out.getvalue())

    def test_tracked_duplicates_are_only_reported_never_deleted(self):
        self._write("src/pkg/copy_a.py", "SAME = 1\n" * 20)
        self._write("src/pkg/copy_b.py", "SAME = 1\n" * 20)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "dups")
        report = cleanup.apply_safe(self.root)
        dup = [c for c in report["delete_candidates"] if c["reason"] == "IDENTICAL_CONTENT"]
        self.assertEqual(dup[0]["paths"], ["src/pkg/copy_a.py", "src/pkg/copy_b.py"])
        self.assertEqual(dup[0]["label"], "DELETE_CANDIDATE")
        self.assertTrue((self.root / "src/pkg/copy_a.py").exists() and (self.root / "src/pkg/copy_b.py").exists())
        self.assertEqual(report["summary"]["tracked_source_deleted"], 0)

    def test_repository_report_keeps_contracts_and_tombstones_protected(self):
        report = cleanup.plan(ROOT)
        labels = {tuple(c["paths"]): c["label"] for c in report["delete_candidates"]}
        self.assertEqual(labels.get(("scripts/ai/run_decision_brain_v3.py", "scripts/ai/run_market_brain.py")),
                         "PROTECTED_KEEP")
        self.assertEqual(json.loads(json.dumps(report))["summary"]["tracked_source_deleted"], 0)


if __name__ == "__main__":
    unittest.main()
