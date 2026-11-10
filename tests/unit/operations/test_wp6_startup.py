"""WP6 regression: reboot readiness, single instance, outage recording, backup/rollback (no VPS, no MT5).

Evidence fixture: the production task XML and launcher exported read-only from the VPS on 4 Nov 2026
(launcher SHA-256 95bf61a9...976e). Production verdict today: NOT_READY (logon-only trigger, autologon off).
"""
import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

from katarina.intelligence.cognition.observer import lock_worker
from katarina.intelligence.operations import data_health, observation_ledger
from katarina.intelligence.operations.startup_task import analyze

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests/fixtures/wp6"
PRODUCTION_XML = (FIXTURES / "observer-task.vps-20261104.xml").read_text(encoding="utf-8")
PRODUCTION_LAUNCHER = (FIXTURES / "run-observer.vps-20261104.ps1").read_text(encoding="utf-8")
PROPOSED_XML = (ROOT / "ops/windows/observer-task.autologon.xml").read_text(encoding="utf-8")
REPO_LAUNCHER = (ROOT / "ops/windows/run-observer.ps1").read_text(encoding="utf-8")
APPLY_SCRIPT = (ROOT / "ops/windows/wp6_apply_observer_startup.ps1").read_text(encoding="utf-8")
U = timezone.utc


def reasons(report):
    return {f["reason"] for f in report["findings"]}


class StartupTaskAnalysisTests(unittest.TestCase):
    def test_production_task_does_not_survive_a_reboot_today(self):
        report = analyze(PRODUCTION_XML, PRODUCTION_LAUNCHER, autologon_enabled=False, autologon_user=None)
        self.assertEqual(report["verdict"], "NOT_READY")
        self.assertEqual(report["mode"], "AUTOLOGON_INTERACTIVE")
        self.assertIn("WP6_NO_AUTOLOGON", reasons(report))
        self.assertIn("WP6_LAUNCHER_ABANDONED_MUTEX_NOT_HANDLED", reasons(report))
        # What production already does right stays green:
        for good in ("WP6_MULTIPLE_INSTANCES_ALLOWED", "WP6_EXECUTION_TIME_LIMIT", "WP6_NO_RESTART_ON_FAILURE",
                     "WP6_ACTION_NOT_CANONICAL_LAUNCHER", "WP6_LAUNCHER_NO_SINGLE_INSTANCE_MUTEX"):
            self.assertNotIn(good, reasons(report))

    def test_proposed_definition_with_owner_autologon_is_ready(self):
        report = analyze(PROPOSED_XML, REPO_LAUNCHER, autologon_enabled=True, autologon_user="WIN-HOST\\Administrator")
        self.assertEqual(report["verdict"], "READY_FOR_REBOOT_TEST", report["findings"])
        self.assertEqual(report["findings"], [])
        self.assertFalse(report["live_execution_authorized"])

    def test_autologon_must_be_known_and_for_the_trigger_user(self):
        unknown = analyze(PROPOSED_XML, REPO_LAUNCHER, autologon_enabled=None, autologon_user=None)
        self.assertIn("WP6_AUTOLOGON_STATE_UNKNOWN", reasons(unknown))
        other = analyze(PROPOSED_XML, REPO_LAUNCHER, autologon_enabled=True, autologon_user="observer")
        self.assertEqual(other["verdict"], "NOT_READY")
        self.assertIn("WP6_AUTOLOGON_USER_MISMATCH", reasons(other))

    def test_boot_trigger_in_session0_needs_isolated_mt5_evidence(self):
        boot = PROPOSED_XML.replace("<LogonTrigger>", "<BootTrigger>").replace("</LogonTrigger>", "</BootTrigger>") \
            .replace("<LogonType>InteractiveToken</LogonType>", "<LogonType>S4U</LogonType>")
        blocked = analyze(boot, REPO_LAUNCHER, autologon_enabled=False, autologon_user=None)
        self.assertEqual((blocked["verdict"], blocked["mode"]), ("BLOCKED_EVIDENCE", "BOOT_NON_INTERACTIVE"))
        self.assertEqual(reasons(blocked), {"WP6_SESSION0_MT5_UNVERIFIED"})
        proven = analyze(boot, REPO_LAUNCHER, autologon_enabled=False, autologon_user=None,
                         session0_mt5_verified=True)
        self.assertEqual(proven["verdict"], "READY_FOR_REBOOT_TEST")

    def test_duplicate_instances_time_limits_and_missing_restart_are_rejected(self):
        bad = (PROPOSED_XML.replace("<MultipleInstancesPolicy>IgnoreNew", "<MultipleInstancesPolicy>Parallel")
               .replace("<ExecutionTimeLimit>PT0S", "<ExecutionTimeLimit>PT72H")
               .replace("<Count>999</Count>", "<Count>1</Count>")
               .replace("<Enabled>true</Enabled>\n    <Hidden>", "<Enabled>false</Enabled>\n    <Hidden>"))
        report = analyze(bad, REPO_LAUNCHER, autologon_enabled=True, autologon_user="Administrator")
        self.assertTrue({"WP6_MULTIPLE_INSTANCES_ALLOWED", "WP6_EXECUTION_TIME_LIMIT", "WP6_NO_RESTART_ON_FAILURE",
                         "WP6_TASK_DISABLED"} <= reasons(report))
        other = PROPOSED_XML.replace("run-observer.ps1", "run-something-else.ps1")
        self.assertIn("WP6_ACTION_NOT_CANONICAL_LAUNCHER",
                      reasons(analyze(other, REPO_LAUNCHER, autologon_enabled=True, autologon_user="Administrator")))
        self.assertEqual(analyze("<Task", REPO_LAUNCHER, autologon_enabled=True, autologon_user="x")["findings"][0]
                         ["reason"], "WP6_TASK_XML_INVALID")

    def test_launcher_without_single_instance_or_stop_marker_is_rejected(self):
        bare = REPO_LAUNCHER.replace("Global\\KatarinaReadonlyObserver", "Local\\x").replace("STOP_OBSERVER", "X")
        report = analyze(PROPOSED_XML, bare, autologon_enabled=True, autologon_user="Administrator")
        self.assertTrue({"WP6_LAUNCHER_NO_SINGLE_INSTANCE_MUTEX", "WP6_LAUNCHER_NO_STOP_MARKER"} <= reasons(report))

    def test_repo_launcher_differs_from_production_only_by_the_abandoned_mutex_fix(self):
        removed = [l for l in PRODUCTION_LAUNCHER.splitlines() if l not in REPO_LAUNCHER.splitlines()]
        self.assertEqual(removed, ["if (-not $mutex.WaitOne(0)) { Write-Log 'already running; exit'; exit 0 }"])
        for invariant in ("--interval-seconds 60 --max-symbols 3", "STOP_OBSERVER", "exit 3", "exit 4",
                          "$mutex.ReleaseMutex()", "catch [System.Threading.AbandonedMutexException]"):
            self.assertIn(invariant, REPO_LAUNCHER)

    def test_cli_offline_reports_production_not_ready(self):
        from scripts.ai import wp6_startup_preflight
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "wp6.json"
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                code = wp6_startup_preflight.main([
                    "--task-xml", str(FIXTURES / "observer-task.vps-20261104.xml"),
                    "--launcher", str(FIXTURES / "run-observer.vps-20261104.ps1"), "--autologon", "0",
                    "--output", str(out)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["verdict"], "NOT_READY")
            self.assertIn("WP6_PREFLIGHT NOT_READY AUTOLOGON_INTERACTIVE", printed.getvalue())


class ApplyScriptSafetyTests(unittest.TestCase):
    def test_dry_run_by_default_backup_before_change_and_restore_on_failure(self):
        script = APPLY_SCRIPT
        self.assertIn("[switch]$Apply", script)
        dry = script.index("if (-not $Apply) {\n    Write-Output 'DRY_RUN")
        backup = script.index("WP6_BACKUP")
        register = script.index("Register-ScheduledTask -TaskName $TaskName -Xml $proposedXml")
        self.assertLess(dry, backup)
        self.assertLess(backup, register)
        self.assertIn("WP6_APPLY_FAILED_RESTORED", script)
        self.assertIn("-Rollback", script)
        code = "\n".join(l for l in script.splitlines() if not l.lstrip().startswith("#"))
        code = code.split("#>", 1)[-1]
        for forbidden in ("Start-ScheduledTask", "Stop-ScheduledTask", "Restart-Computer", "Stop-Process",
                          "Autologon.exe", "DefaultPassword", "Unregister-ScheduledTask", "MetaTrader"):
            self.assertNotIn(forbidden, code)

    def test_powershell_parses_the_scripts_when_available(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            self.skipTest("PowerShell not installed")
        for path in ("ops/windows/wp6_apply_observer_startup.ps1", "ops/windows/run-observer.ps1",
                     "ops/windows/run-stage0-health-since-wp12.ps1"):
            check = ("$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
                     f"'{ROOT / path}',[ref]$null,[ref]$e);if($e){{$e;exit 1}}")
            result = subprocess.run([shell, "-NoProfile", "-Command", check], capture_output=True, text=True,
                                    timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class PowerShell4CompatibilityTests(unittest.TestCase):
    """The VPS is Windows Server 2012 R2 with PowerShell 4.0 (deploy 4 Nov 2026: `::new()` failed there)."""

    PS5_ONLY = ("::new(", "using namespace", "class ", "enum ", "Get-FileHash -InputStream", "-AsHashtable")

    def test_ops_windows_scripts_avoid_powershell5_only_syntax(self):
        for path in sorted((ROOT / "ops/windows").glob("*.ps1")):
            code = "\n".join(l for l in path.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))
            for token in self.PS5_ONLY:
                with self.subTest(script=path.name, token=token):
                    self.assertNotIn(token, code)


class Stage0SidecarTests(unittest.TestCase):
    def test_sidecar_uses_deployed_checker_and_official_count_start(self):
        text = (ROOT / "ops/windows/run-stage0-health-since-wp12.ps1").read_text(encoding="utf-8")
        self.assertIn("$code  = 'C:\\Katarina\\code'", text)
        self.assertIn("--since official", text)
        self.assertNotIn("_audit_20261103_main", text)  # the stale pinned pre-K-04 checkout
        self.assertNotIn("b3fd2e6063695358bf50f2e316388ac945079fd7", text)
        code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
        for forbidden in ("Remove-Item", "Stop-", "Restart-", "order"):
            self.assertNotIn(forbidden, code)


class RestartBehaviourTests(unittest.TestCase):
    def test_second_observer_is_refused_and_lock_recovers_after_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = lock_worker(Path(tmp))
            with self.assertRaisesRegex(RuntimeError, "^CONTEXTUAL_OBSERVER_ALREADY_RUNNING$"):
                lock_worker(Path(tmp))
            first.close()  # a crashed process releases its OS file lock
            lock_worker(Path(tmp)).close()

    def test_reboot_gap_is_an_outage_without_duplicate_cycles_or_orders(self):
        db = sqlite3.connect(":memory:")
        observation_ledger.setup(db)
        start = datetime(2026, 11, 4, 10, tzinfo=U)
        moments = [start + timedelta(minutes=m) for m in range(30)]
        moments += [start + timedelta(minutes=45 + m) for m in range(30)]  # 15 min reboot
        for moment in moments:
            db.execute("INSERT INTO observer_cycles(cycle_id, observed_utc, finished_utc, status, clock_shift_hours, "
                       "symbols_observed, symbols_with_quote, orders_submitted) VALUES(?,?,?,?,?,?,?,0)",
                       ("c-" + moment.isoformat(), moment.isoformat(), moment.isoformat(), "OK", 2.0, 5, 5))
        report = data_health.assess(db, datetime(2026, 11, 4, 12, tzinfo=U))
        db.close()
        self.assertEqual(report["observer_outages"], [{
            "start_utc": (start + timedelta(minutes=29)).isoformat(),
            "end_utc": (start + timedelta(minutes=45)).isoformat(), "seconds": 960}])
        criteria = {c["criterion"]: c for c in report["criteria"]}
        self.assertEqual(criteria["no_duplicates_monotonic"]["duplicate_cycles"], 0)
        self.assertEqual(criteria["zero_orders"]["status"], "PASS")
        self.assertEqual(report["cycles_total"], 60)  # the gap is never backfilled


if __name__ == "__main__":
    unittest.main()
