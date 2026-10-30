"""Synthetic OS status tests, never operational NTP evidence."""
from datetime import datetime, timedelta, timezone
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from katarina.intelligence.broker.host_clock_probe import (
    inspect_windows_host_clock, parse_w32tm_status,
)

NOW = datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc)
STATUS = """Leap Indicator: 0(no warning)
Stratum: 5 (secondary reference - syncd by (S)NTP)
Source: time.windows.com,0x8
Phase Offset: 0.0348339s
State Machine: 2 (Sync)
Last Sync Error: 0 (The command completed successfully.)
Time since Last Good Sync Time: 123.45s
"""


class HostClockProbeTests(unittest.TestCase):
    def test_valid_status_preserves_measured_age_and_offset(self):
        result = parse_w32tm_status(STATUS, NOW, 10.)
        self.assertTrue(result.trusted)
        self.assertEqual(result.last_sync_utc, NOW - timedelta(seconds=123.45))
        self.assertEqual(result.offset_seconds, .0348339)
        self.assertEqual(result.source, "time.windows.com")
        self.assertTrue(result.current_at(NOW + timedelta(seconds=2), 12.))
        self.assertFalse(result.current_at(NOW + timedelta(hours=1), 12.))
        self.assertFalse(result.current_at(NOW + timedelta(seconds=11), 21.))
        self.assertFalse(result.current_at(NOW, 9.))

    def test_every_required_field_is_required(self):
        for line in STATUS.splitlines():
            with self.subTest(line=line):
                raw = STATUS.replace(line + "\n", "")
                self.assertFalse(parse_w32tm_status(raw, NOW, 10.).trusted)

    def test_invalid_or_unsynced_fields_fail_closed(self):
        for old, new in (
            ("0(no warning)", "3(not synchronized)"),
            ("Stratum: 5", "Stratum: 0"),
            ("Stratum: 5", "Stratum: 16"),
            ("2 (Sync)", "1 (Hold)"),
            ("Last Sync Error: 0", "Last Sync Error: 5"),
            ("123.45s", "14401s"),
            ("123.45s", "-1s"),
            ("0.0348339s", "2.0s"),
            ("0.0348339s", "NaNs"),
            ("0.0348339s", "0,0348339s"),
            ("time.windows.com,0x8", "Local CMOS Clock"),
            ("time.windows.com,0x8", "evil-time.windows.com"),
            ("time.windows.com,0x8", "time.windows.com.evil.example"),
            ("time.windows.com,0x8", "VM IC Time Synchronization Provider"),
        ):
            with self.subTest(new=new):
                self.assertFalse(parse_w32tm_status(STATUS.replace(old, new), NOW, 10.).trusted)
        self.assertFalse(parse_w32tm_status(STATUS + "Stratum: 1\n", NOW, 10.).trusted)

    def test_non_windows_does_not_trust_or_run_a_command(self):
        with patch("platform.system", return_value="Linux"), patch("subprocess.run") as run:
            result = inspect_windows_host_clock()
        self.assertFalse(result.trusted)
        run.assert_not_called()

    def test_production_inspector_ignores_test_environment_flags(self):
        from katarina.intelligence.broker.broker_clock_alignment import inspect_host_clock
        with patch("platform.system", return_value="Linux"), patch.dict(
                "os.environ", {"KATARINA_TEST_HOST_CLOCK_TRUST":"1"}):
            self.assertFalse(inspect_host_clock().trusted)

    def test_timeout_failure_and_unavailable_command(self):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired("w32tm", 3)):
            with self.subTest(error=type(error).__name__):
                with patch("platform.system", return_value="Windows"), patch("subprocess.run", side_effect=error):
                    self.assertFalse(inspect_windows_host_clock().trusted)
        with patch("platform.system", return_value="Windows"), patch("subprocess.run", return_value=SimpleNamespace(returncode=1)):
            self.assertFalse(inspect_windows_host_clock().trusted)

    def test_os_adapter_requires_verbose_and_bounded_query(self):
        with patch("platform.system", return_value="Windows"), patch("subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=STATUS)) as run:
            self.assertTrue(inspect_windows_host_clock().trusted)
        self.assertEqual(run.call_args.args[0], ["w32tm", "/query", "/status", "/verbose"])
        self.assertEqual(run.call_args.kwargs["timeout"], 3)

    def test_clock_step_during_os_query_is_rejected(self):
        with patch("platform.system", return_value="Windows"), patch("subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=STATUS)), patch("katarina.intelligence.broker.host_clock_probe.datetime") as clock, patch("time.monotonic", side_effect=[10., 11.]):
            clock.now.side_effect = [NOW, NOW + timedelta(hours=1, seconds=1)]
            result = inspect_windows_host_clock()
        self.assertFalse(result.trusted)
        self.assertEqual(result.reason, "HOST_UTC_STEP_DETECTED")
