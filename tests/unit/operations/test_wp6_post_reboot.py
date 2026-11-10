"""WP6 post-reboot readiness: READY_AFTER_REBOOT only from evidence of a real reboot (K3)."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.intelligence.operations import observation_ledger, post_reboot

BOOT0 = datetime(2026, 10, 4, 9, 0, tzinfo=timezone.utc)
BOOT1 = datetime(2026, 11, 14, 6, 0, tzinfo=timezone.utc)      # planned reboot, Saturday
ROOT = Path(__file__).resolve().parents[3]

WMIC = """

CommandLine="C:\\Program Files\\MetaTrader 5\\terminal64.exe"
ExecutablePath=C:\\Program Files\\MetaTrader 5\\terminal64.exe
Name=terminal64.exe
ParentProcessId=6944
ProcessId=6964
SessionId=2


CommandLine="C:\\Katarina\\code\\.katarina-envs\\env-x\\Scripts\\python.exe"  scripts\\ai\\run_contextual_market_observer.py --continuous
ExecutablePath=C:\\Katarina\\code\\.katarina-envs\\env-x\\Scripts\\python.exe
Name=python.exe
ParentProcessId=6552
ProcessId=2304
SessionId=2


CommandLine="C:\\Katarina\\python312\\python.exe" scripts\\ai\\run_contextual_market_observer.py --continuous
ExecutablePath=C:\\Katarina\\python312\\python.exe
Name=python.exe
ParentProcessId=2304
ProcessId=6280
SessionId=2

"""


def make_db(path, cycles):
    Path(path).unlink(missing_ok=True)
    db = sqlite3.connect(path)
    observation_ledger.setup(db)
    for i, (when, status, shift, orders) in enumerate(cycles):
        db.execute("INSERT INTO observer_cycles(cycle_id, observed_utc, status, clock_shift_hours, orders_submitted) "
                   "VALUES(?,?,?,?,?)", (f"c-{i}", when.isoformat(), status, shift, orders))
    db.commit()
    db.close()


def base():
    return post_reboot.baseline(boot_utc=BOOT0, now_utc=BOOT1 - timedelta(hours=1), task_xml_sha256="t",
                                launcher_sha256="l", observers=[{}], mt5=[{}],
                                ledger={"orders_submitted_total": 0, "quick_check": "ok"})


class ParsingTests(unittest.TestCase):
    def test_venv_redirector_chain_counts_as_one_observer(self):
        observers, mt5 = post_reboot.classify_processes(post_reboot.parse_wmic_list(WMIC))
        self.assertEqual([2304], [o["pid"] for o in observers])
        self.assertEqual([6280], observers[0]["child_pids"])
        self.assertEqual([6964], [m["pid"] for m in mt5])

    def test_wmi_datetime_offset(self):
        self.assertEqual(datetime(2026, 10, 4, 2, 30, 15, tzinfo=timezone.utc),
                         post_reboot.parse_wmi_datetime("20261004093015.500000+420"))


class AssessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "context.sqlite3"
        self.obs, self.mt5 = [{"pid": 1, "session_id": 2}], [{"pid": 2, "session_id": 2}]

    def tearDown(self):
        self.tmp.cleanup()

    def assess(self, cycles, *, boot=BOOT1, observers=None, mt5=None, baseline="default"):
        make_db(self.db, cycles)
        ledger = post_reboot.read_ledger(self.db, boot)
        return post_reboot.assess(base=base() if baseline == "default" else baseline, boot_utc=boot,
                                  now_utc=boot + timedelta(hours=1), observers=self.obs if observers is None else observers,
                                  mt5=self.mt5 if mt5 is None else mt5, ledger=ledger, task_xml_sha256="t",
                                  launcher_sha256="l")

    def healthy(self):
        return [(BOOT1 - timedelta(minutes=10), "OK", 2.0, 0), (BOOT1 + timedelta(minutes=4), "OK", 2.0, 0),
                (BOOT1 + timedelta(minutes=5), "OK", 2.0, 0)]

    def reasons(self, report):
        return [f["reason"] for f in report["findings"]]

    def test_ready_only_after_real_reboot(self):
        report = self.assess(self.healthy())
        self.assertEqual("READY_AFTER_REBOOT", report["verdict"], report["findings"])
        self.assertFalse(report["live_execution_authorized"])

    def test_without_reboot_or_baseline_is_not_tested(self):
        self.assertEqual("NOT_TESTED", self.assess(self.healthy(), boot=BOOT0)["verdict"])
        self.assertEqual("NOT_TESTED", self.assess(self.healthy(), baseline=None)["verdict"])

    def test_two_observers_or_session0_mt5_fail(self):
        two = self.assess(self.healthy(), observers=self.obs + [{"pid": 9, "session_id": 2}])
        self.assertIn("WP6_OBSERVER_COUNT", self.reasons(two))
        s0 = self.assess(self.healthy(), mt5=[{"pid": 2, "session_id": 0}])
        self.assertIn("WP6_NOT_SAME_INTERACTIVE_SESSION", self.reasons(s0))
        self.assertEqual("NOT_READY", s0["verdict"])

    def test_orders_late_cycle_and_backfill_fail(self):
        orders = self.assess(self.healthy()[:-1] + [(BOOT1 + timedelta(minutes=5), "OK", 2.0, 1)])
        self.assertIn("WP6_ORDERS_RECORDED", self.reasons(orders))
        late = self.assess([(BOOT1 - timedelta(minutes=10), "OK", 2.0, 0), (BOOT1 + timedelta(minutes=45), "OK", 2.0, 0)])
        self.assertIn("WP6_FIRST_CYCLE_LATE", self.reasons(late))
        backfill = self.assess([(BOOT1 - timedelta(seconds=30), "OK", 2.0, 0), (BOOT1 + timedelta(seconds=30), "OK", 2.0, 0)])
        self.assertIn("WP6_REBOOT_GAP_NOT_VISIBLE", self.reasons(backfill))
        no_clock = self.assess([(BOOT1 - timedelta(minutes=10), "OK", 2.0, 0), (BOOT1 + timedelta(minutes=4), "OK", None, 0)])
        self.assertIn("WP6_NO_OK_CYCLE_AFTER_BOOT", self.reasons(no_clock))

    def test_ledger_is_opened_read_only(self):
        make_db(self.db, self.healthy())
        before = self.db.read_bytes()
        post_reboot.read_ledger(self.db, BOOT1)
        self.assertEqual(before, self.db.read_bytes())

    def test_backup_copies_and_checks_integrity_without_overwrite(self):
        make_db(self.db, self.healthy())
        out = Path(self.tmp.name) / "backup"
        result = post_reboot.backup_database(self.db, out)
        self.assertEqual("ok", result["integrity_check"])
        with self.assertRaises(FileExistsError):
            post_reboot.backup_database(self.db, out)


class ScriptSafetyTests(unittest.TestCase):
    def test_cli_has_no_side_effect_commands(self):
        text = (ROOT / "scripts" / "ai" / "wp6_reboot_check.py").read_text(encoding="utf-8").lower()
        for forbidden in ("shutdown", "restart-computer", "/run", "/end", "taskkill", "stop-process",
                          "autoadminlogon", "defaultpassword", "order_send", "initialize("):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
