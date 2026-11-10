"""KAT-CG coding gate acceptance (AUTO_CLEANUP_CODING_GATE.md section E) on isolated fixture repos.

Each test copies the tracked repository into a temporary git repo, breaks it on purpose and proves
the gate turns red with file:line, never repairs anything itself, and stops repeated failures.
"""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("code_change_gate", ROOT / "scripts/governance/code_change_gate.py")
gate = importlib.util.module_from_spec(spec)
sys.modules["code_change_gate"] = gate  # dataclasses resolve annotations via sys.modules
spec.loader.exec_module(gate)
GIT_ENV = {"GIT_AUTHOR_NAME": "gate-test", "GIT_AUTHOR_EMAIL": "gate@test.invalid",
           "GIT_COMMITTER_NAME": "gate-test", "GIT_COMMITTER_EMAIL": "gate@test.invalid"}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, env=dict(os.environ, **GIT_ENV)).stdout


class FixtureRepo:
    """Tracked files of this checkout committed into a throwaway repo (no network, no history)."""

    _template = None

    @classmethod
    def template(cls):
        if cls._template is None:
            cls._tmp = tempfile.TemporaryDirectory()
            base = Path(cls._tmp.name) / "template"
            files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], stdout=subprocess.PIPE,
                                   check=True).stdout.decode("utf-8", "surrogateescape").split("\0")
            for rel in filter(None, files):
                source = ROOT / rel
                if source.is_file():
                    target = base / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            git(base, "init", "-q", "-b", "fixture")
            git(base, "config", "core.autocrlf", "false")
            git(base, "add", "-A")
            git(base, "commit", "-q", "-m", "fixture")
            cls._template = base
        return cls._template

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(self.template(), self.root, symlinks=True)

    def commit(self, message):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", message)

    def run(self, gates, **kwargs):
        kwargs.setdefault("ledger_path", self.root / "build" / "code-gate" / "failure-ledger.json")
        return gate.run(self.root, gates, **kwargs)

    def close(self):
        self.tmp.cleanup()


def findings(report, gate_id):
    return [f for g in report["gates"] if g["gate"] == gate_id for f in g["findings"]]


class CodeChangeGateTests(unittest.TestCase):
    def setUp(self):
        self.repo = FixtureRepo()

    def tearDown(self):
        self.repo.close()

    def test_clean_fixture_passes_quick_and_safety_gates(self):
        report = self.repo.run(["KAT-CG-00", "KAT-CG-01", "KAT-CG-03"])
        self.assertEqual(report["result"], "PASS", json.dumps(report["gates"], indent=1)[:2000])
        self.assertEqual(report["orders_submitted"], 0)
        self.assertFalse(report["live_execution_authorized"])

    def test_broken_python_and_json_fail_cg01_with_file_line_then_recover(self):
        target = self.repo.root / "src/katarina/domain/market_calendar.py"
        original = target.read_text(encoding="utf-8")
        target.write_text(original + "\ndef broken(:\n", encoding="utf-8")
        config = self.repo.root / "config/observer_universe.json"
        config_text = config.read_text(encoding="utf-8")
        config.write_text('{\n  "symbols": [\n', encoding="utf-8")
        report = self.repo.run(["KAT-CG-00", "KAT-CG-01", "KAT-CG-02"])
        self.assertEqual(report["result"], "FAIL_SYNTAX_OR_DEPENDENCY")
        locations = {(f["reason"], f["file"]) for f in findings(report, "KAT-CG-01")}
        self.assertIn(("PYTHON_SYNTAX_ERROR", "src/katarina/domain/market_calendar.py"), locations)
        self.assertIn(("JSON_INVALID", "config/observer_universe.json"), locations)
        syntax = next(f for f in findings(report, "KAT-CG-01") if f["reason"] == "PYTHON_SYNTAX_ERROR")
        self.assertEqual(syntax["line"], original.count("\n") + 2)
        self.assertTrue(syntax["error_id"].startswith("KAT-ERR-"))
        self.assertEqual(report["not_run"], ["KAT-CG-02"])  # fail-fast: tests never ran
        target.write_text(original, encoding="utf-8")
        config.write_text(config_text, encoding="utf-8")
        self.assertEqual(self.repo.run(["KAT-CG-01"])["result"], "PASS")

    def test_broken_import_and_mql_include_fail_cg01(self):
        module = self.repo.root / "src/katarina/domain/market_calendar.py"
        module.write_text("from katarina.domain.no_such_module import x\n" + module.read_text(encoding="utf-8"),
                          encoding="utf-8")
        ea = self.repo.root / "mt5/Experts/KatarinaBridgeEA.mq5"
        ea.write_text('#include <Katarina/NoSuchInclude.mqh>\n' + ea.read_text(encoding="utf-8"), encoding="utf-8")
        report = self.repo.run(["KAT-CG-01"])
        self.assertEqual(report["result"], "FAIL_SYNTAX_OR_DEPENDENCY")
        details = " ".join(f["detail"] for f in findings(report, "KAT-CG-01"))
        self.assertIn("katarina.domain.no_such_module", details)
        self.assertIn("NoSuchInclude.mqh", details)
        self.assertTrue(any(f["file"] == "src/katarina/domain/market_calendar.py" and f["line"] == 1
                            for f in findings(report, "KAT-CG-01")))

    def test_tracked_env_file_fails_without_printing_secret(self):
        secret = "KATARINA_TEST_SECRET_VALUE_9f2c"
        (self.repo.root / ".env").write_text("API_KEY=" + secret + "\n", encoding="utf-8")
        git(self.repo.root, "add", "-f", ".env")
        report = self.repo.run(["KAT-CG-01"])
        self.assertEqual(report["result"], "FAIL_SYNTAX_OR_DEPENDENCY")
        self.assertIn(("TRACKED_JUNK_OR_SECRET_NAME", ".env"),
                      {(f["reason"], f["file"]) for f in findings(report, "KAT-CG-01")})
        self.assertNotIn(secret, json.dumps(report))

    def test_manifest_drift_and_locked_file_fail_cg03_without_auto_repair(self):
        manifest = self.repo.root / "ops/deployment/release-manifest.json"
        before = manifest.read_bytes()
        observer = self.repo.root / "src/katarina/intelligence/cognition/observer.py"
        observer.write_text(observer.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
        risk = self.repo.root / "src/katarina/engines/risk.py"
        risk.write_text(risk.read_text(encoding="utf-8") + "\n# weakened?\n", encoding="utf-8")
        report = self.repo.run(["KAT-CG-03"])
        self.assertEqual(report["result"], "FAIL_SAFETY_OR_MANIFEST")
        reasons = {(f["reason"], f["file"]) for f in findings(report, "KAT-CG-03")}
        self.assertIn(("MANIFEST_CHANGED", "src/katarina/intelligence/cognition/observer.py"), reasons)
        self.assertTrue(any(r == "PROMOTION_LOCK_VIOLATION" and "risk.py" in f for r, f in reasons)
                        or any(f["reason"] == "PROMOTION_LOCK_VIOLATION" and "risk.py" in f["detail"]
                               for f in findings(report, "KAT-CG-03")))
        self.assertEqual(manifest.read_bytes(), before)  # never regenerated by the gate
        self.assertIn("# weakened?", risk.read_text(encoding="utf-8"))  # never reverted silently

    def test_conflict_marker_blocks_baseline(self):
        doc = self.repo.root / "docs/README.md"
        doc.write_text(doc.read_text(encoding="utf-8") + "\n<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> x\n",
                       encoding="utf-8")
        report = self.repo.run(["KAT-CG-00", "KAT-CG-01"])
        self.assertEqual(report["result"], "BLOCKED_BASELINE")
        self.assertEqual(findings(report, "KAT-CG-00")[0]["reason"], "MERGE_CONFLICT_MARKER")
        self.assertEqual(gate.exit_code(report["result"]), 2)

    def test_repeated_failure_after_one_fix_attempt_stops_until_root_cause(self):
        target = self.repo.root / "config/observer_universe.json"
        good = target.read_text(encoding="utf-8")
        target.write_text("{broken", encoding="utf-8")
        self.repo.commit("introduce bug")
        first = self.repo.run(["KAT-CG-01"])
        self.assertEqual(first["result"], "FAIL_SYNTAX_OR_DEPENDENCY")
        fp = findings(first, "KAT-CG-01")[0]["fingerprint"]
        self.assertEqual(self.repo.run(["KAT-CG-01"])["result"], "FAIL_SYNTAX_OR_DEPENDENCY")  # same HEAD: no attempt
        target.write_text("{still broken", encoding="utf-8")  # a "fix" that does not fix the root cause
        self.repo.commit("attempted fix")
        second = self.repo.run(["KAT-CG-01"])
        self.assertEqual(second["result"], gate.REPEATED)
        self.assertEqual(gate.exit_code(second["result"]), 3)
        third = self.repo.run(["KAT-CG-01"])  # STOP: no gate runs, no endless retry
        self.assertEqual(third["result"], gate.REPEATED)
        self.assertEqual(third["gates"], [])
        ledger = gate.FailureLedger(self.repo.root / "build/code-gate/failure-ledger.json")
        with self.assertRaises(SystemExit):
            ledger.record_root_cause(fp, "", "")  # analysis and reproduction test are mandatory
        blocked = {e["fingerprint"] for e in ledger.blocked()}
        self.assertIn(fp, blocked)  # every repeated fingerprint (own JSON check + dependency audit) is stopped
        for other in blocked:
            ledger.record_root_cause(other, "config written by hand without JSON validation",
                                     "tests/static/test_code_change_gate.py")
        ledger.save()
        self.assertEqual(ledger.blocked(), [])
        target.write_text(good, encoding="utf-8")
        self.repo.commit("real fix")
        fixed = self.repo.run(["KAT-CG-01"])
        self.assertEqual(fixed["result"], "PASS")
        entry = gate.FailureLedger(self.repo.root / "build/code-gate/failure-ledger.json").data["entries"][fp]
        self.assertEqual(entry["status"], "VERIFIED")
        self.assertEqual(entry["fix_commit"], git(self.repo.root, "rev-parse", "HEAD").strip())
        self.assertEqual(entry["reproduction_test"], "tests/static/test_code_change_gate.py")


class RemoteGateTests(unittest.TestCase):
    def test_anonymous_https_fetch_reads_actual_public_ci_schema(self):
        path = "repos/owner/repo/commits/" + "a" * 40 + "/check-runs?per_page=100"
        response = {"check_runs": [{"name": "body", "conclusion": "success"}]}
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GH_TOKEN": ""}):
            with patch("urllib.request.urlopen",
                       return_value=io.BytesIO(json.dumps(response).encode("utf-8"))) as read:
                with patch.object(gate.subprocess, "run",
                                  side_effect=AssertionError("CLI must not be needed")):
                    data = gate._github_json(path)
        self.assertEqual(data, response)
        req = read.call_args.args[0]
        self.assertEqual(req.full_url, "https://api.github.com/" + path)
        self.assertIsNone(req.get_header("Authorization"))

    def test_public_ci_lookup_fails_closed_if_network_or_payload_is_invalid(self):
        path = "repos/owner/repo/commits/" + "b" * 40 + "/check-runs?per_page=100"
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GH_TOKEN": ""}):
            for payload in (b"{invalid-json", b'{"check_runs": null}', b'{"message":"rate limited"}'):
                with self.subTest(payload=payload):
                    with patch("urllib.request.urlopen", return_value=io.BytesIO(payload)):
                        with patch.object(gate.subprocess, "run", side_effect=OSError("no gh")):
                            self.assertIsNone(gate._github_json(path))
            with patch("urllib.request.urlopen", side_effect=OSError("network offline")):
                with patch.object(gate.subprocess, "run", side_effect=OSError("no gh")):
                    self.assertIsNone(gate._github_json(path))
            with patch("urllib.request.urlopen", side_effect=AssertionError("bad URL must be rejected")):
                self.assertIsNone(gate._github_json("https://untrusted.invalid/" + path))

    def test_rejected_explicit_ci_credential_is_never_downgraded_to_anonymous(self):
        path = "repos/owner/repo/commits/" + "c" * 40 + "/check-runs?per_page=100"
        with patch.dict(os.environ, {"GITHUB_TOKEN": "bad-token", "GH_TOKEN": ""}):
            with patch("urllib.request.urlopen", side_effect=OSError("403")):
                with patch.object(gate.subprocess, "run",
                                  side_effect=AssertionError("must not use unauthenticated fallback")):
                    self.assertIsNone(gate._github_json(path))

    def test_ci_gate_blocks_without_evidence_or_with_failed_check(self):
        with patch.object(gate, "_github_json", return_value=None):
            report = gate.gate_04(ROOT, "0" * 40, "o/r")
        self.assertEqual(report.findings[0].reason, "CI_STATUS_UNAVAILABLE")
        runs = {"check_runs": [
            {"name": "body", "conclusion": "success", "started_at": "1"},
            {"name": "Portable brain (ubuntu-latest)", "conclusion": "success", "started_at": "1"},
            {"name": "Portable brain (windows-latest)", "conclusion": "failure", "started_at": "1"},
            {"name": "Portable brain (windows-latest)", "conclusion": "success", "started_at": "0"}]}
        with patch.object(gate, "_github_json", return_value=runs):
            report = gate.gate_04(ROOT, "0" * 40, "o/r")
        self.assertEqual([(f.reason, f.test) for f in report.findings],
                         [("CI_CHECK_NOT_SUCCESS", "Portable brain (windows-latest)")])

    def test_deploy_gate_blocks_without_receipt_and_never_contacts_vps(self):
        report = gate.gate_05(ROOT, "0" * 40, "o/r", None)
        self.assertEqual(report.findings[0].reason, "DEPLOY_RECEIPT_MISSING")
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "deploy.json"
            receipt.write_text(json.dumps({"target_sha": "1" * 40, "backup_path": "x", "backup_integrity": "ok",
                                           "rollback_sha": "2" * 40, "rollback_steps": ["checkout"],
                                           "owner_approval_ref": "", "smoke_orders_submitted": 1,
                                           "live_execution": False}), encoding="utf-8")
            with patch.object(gate, "_github_json", return_value=None):
                report = gate.gate_05(ROOT, "0" * 40, "o/r", receipt)
        reasons = {f.reason for f in report.findings}
        self.assertTrue({"TARGET_SHA_MISMATCH", "OWNER_APPROVAL_MISSING", "SMOKE_NOT_READONLY"} <= reasons)
        self.assertIn("UPSTREAM_KAT_CG_04_CI_STATUS_UNAVAILABLE", reasons)


class WorkflowWiringTests(unittest.TestCase):
    def test_body_ci_runs_gate_ids_and_has_no_schedule(self):
        workflow = (ROOT / ".github/workflows/katarina-body-ci.yml").read_text(encoding="utf-8")
        for gate_id in ("KAT-CG-00", "KAT-CG-01", "KAT-CG-02", "KAT-CG-03"):
            self.assertIn(gate_id, workflow)
        self.assertIn("scripts/governance/code_change_gate.py", workflow)
        self.assertIn("scripts/governance/safe_cleanup.py --check", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("needs: [body, portable-host]", workflow)  # KAT-CG-04 aggregate CI check

    def test_local_pre_commit_hook_runs_quick_gate(self):
        hook = (ROOT / "ops/git-hooks/pre-commit").read_text(encoding="utf-8")
        self.assertIn("code_change_gate.py\" --quick", hook)
        self.assertIn("exit $status", hook)


if __name__ == "__main__":
    unittest.main()
