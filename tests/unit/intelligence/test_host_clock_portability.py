"""Host UTC and MT5 server UTC portability checks; all offline and read-only."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from katarina.intelligence.broker.host_clock_guard import (
    assess_windows_status, inspect_host_clock, require_host_clock)
from katarina.intelligence.broker.broker_clock_alignment import (
    infer_clock_shift, corroborate_clock_with_utc_history)


class HostClockPortableTests(unittest.TestCase):
    WINDOWS_VALID = (
        "Leap Indicator: 0(no warning)\nStratum: 3\n"
        "Last Successful Sync Time: 10/28/2026 00:59:11\n"
        "Source: time.windows.com,0x9\n"
    )
    WINDOWS_CMOS = (
        "Leap Indicator: 3(last minute has 61 seconds)\nStratum: 0\n"
        "Last Successful Sync Time: unspecified\nSource: Local CMOS Clock\n"
    )

    def test_unsynchronized_actual_vps_report_is_rejected(self):
        status = assess_windows_status(self.WINDOWS_CMOS)
        self.assertFalse(status.synchronized)
        self.assertEqual(status.reason, "HOST_UTC_NOT_SYNCHRONIZED")

    def test_windows_ntp_report_is_accepted_only_as_os_attestation(self):
        status = assess_windows_status(
            self.WINDOWS_VALID, now_local=datetime(2026,10,28,1,5))
        self.assertTrue(status.synchronized)
        self.assertFalse(status.live_authorized)

    def test_real_native_route_refuses_to_initialize_without_ntp(self):
        from unittest.mock import patch
        from katarina.adapters.automatic_connection import (
            BoundLocalBroker, ConnectionConfig, ConnectionUnavailable)
        class Native:
            __name__ = "MetaTrader5"
            calls = 0
            def initialize(self, *a):
                self.calls += 1
                return True
            def shutdown(self):
                pass

        native=Native()
        broker=BoundLocalBroker(native,ConnectionConfig(
            expected_login=11,expected_server="synthetic-demo"))
        with patch("katarina.intelligence.broker.host_clock_guard.require_host_clock",
                   side_effect=RuntimeError("HOST_UTC_NOT_SYNCHRONIZED")):
            with self.assertRaises(ConnectionUnavailable):
                broker.initialize()
        self.assertEqual(native.calls,0)

    def test_windows_stale_sync_is_blocked(self):
        bad=assess_windows_status(
            self.WINDOWS_VALID, now_local=datetime(2026,10,29,16,5))
        self.assertEqual(bad.reason, "HOST_CLOCK_LAST_SYNC_STALE")
        self.assertFalse(bad.synchronized)

    def test_unsupported_locale_fails_closed(self):
        self.assertFalse(assess_windows_status("Sumber: CMOS\n").synchronized)

    def test_ntp_linux_and_absent_service_fail_closed(self):
        def runner(output,code=0):
            return lambda *a,**k: SimpleNamespace(stdout=output,returncode=code)
        self.assertTrue(inspect_host_clock(platform="linux",run=runner("yes\n")).synchronized)
        for response in ("no\n", "unknown\n", ""):
            self.assertFalse(inspect_host_clock(platform="linux",run=runner(response)).synchronized)
        self.assertFalse(inspect_host_clock(platform="linux",run=runner("yes\n",1)).synchronized)
        with self.assertRaisesRegex(RuntimeError, "HOST_UTC_NOT_SYNCHRONIZED"):
            require_host_clock(platform="linux",run=runner("no\n"))

    def test_windows_runner_attestation_and_missing_command(self):
        # Match the runner's own local calendar regardless of its timezone.
        stamp=datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        source=self.WINDOWS_VALID.replace("10/28/2026 00:59:11",stamp)
        runner=lambda *a,**k: SimpleNamespace(stdout=source,returncode=0)
        self.assertTrue(inspect_host_clock(platform="win32",run=runner).synchronized)
        def absent(*a,**k):
            raise FileNotFoundError("missing")
        self.assertEqual(inspect_host_clock(platform="win32",run=absent).reason,
                         "HOST_CLOCK_STATUS_UNAVAILABLE")


class BrokerClockPortabilityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,10,28,9,0,tzinfo=timezone.utc).timestamp()
        self.symbols = ("EURUSD","GBPUSD","USDJPY")
        self.raw = {x:int(self.now+3*3600-2) for x in self.symbols}
        self.history = {x:(1.1000,1.1002,self.now-2) for x in self.symbols}

    def test_crosscheck_requires_independent_recent_history_quorum(self):
        finding=infer_clock_shift(self.raw,self.now)
        self.assertTrue(corroborate_clock_with_utc_history(
            finding,self.raw,self.history,self.now))
        self.assertFalse(corroborate_clock_with_utc_history(
            finding,self.raw,{},self.now))

    def test_crosscheck_rejects_mismatched_server_offset_and_stale_ticks(self):
        finding=infer_clock_shift(self.raw,self.now)
        late={x:(1.1,1.2,self.now-170) for x in self.symbols}
        self.assertFalse(corroborate_clock_with_utc_history(
            finding,self.raw,late,self.now))
        bad={x:(1.1,1.2,self.now-65) for x in self.symbols}
        self.assertFalse(corroborate_clock_with_utc_history(
            finding,self.raw,bad,self.now))

    def test_weekend_stale_quote_cannot_be_a_negative_time_zone(self):
        now=datetime(2026,10,24,3,57,tzinfo=timezone.utc).timestamp()
        stale={x:int(now-4*3600) for x in self.symbols}
        finding=infer_clock_shift(stale,now)
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertIsNone(finding.observed_hours_shift)

    def test_utc_clock_fresh_quote_and_device_timezone_independent(self):
        zone=timezone(timedelta(hours=7))
        now=datetime(2026,10,28,16,0,tzinfo=zone).timestamp()
        raw={x:int(now-2) for x in self.symbols}
        hist={x:(1.1,1.2,now-2) for x in self.symbols}
        finding=infer_clock_shift(raw,now)
        self.assertEqual(finding.observed_hours_shift,0)
        self.assertTrue(corroborate_clock_with_utc_history(
            finding,raw,hist,now))


if __name__=="__main__":
    unittest.main()
