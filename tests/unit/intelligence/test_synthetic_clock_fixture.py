"""Calendar-stable synthetic clock fixture; production market-close guard unchanged."""
import unittest
from datetime import datetime, timezone

from katarina.intelligence.broker.broker_clock_alignment import HostClockTrust, infer_clock_shift
from katarina.intelligence.broker import live_clock_probe
from tests.synthetic_clock_fixture import ModuleClockFixture


class ClockFixtureScopeTests(unittest.TestCase):
    def test_real_weekend_guard_restored_after_synthetic_test_scope(self):
        closed = datetime(2026, 10, 30, 21, 30, tzinfo=timezone.utc)
        epoch = int(closed.timestamp())
        ticks = {s: epoch + 3 * 3600 for s in ("EURUSD", "GBPUSD", "USDJPY")}
        trust = HostClockTrust(True, "TRUSTED_HOST_NTP", "SYNTHETIC_TEST_ONLY", closed, 0.)
        options = {"host_trust": trust, "require_host_trust": True, "broker_server": "Synthetic"}
        self.assertEqual(infer_clock_shift(ticks, epoch, **options).reason, "FX_MARKET_CLOSED")

        fixture = ModuleClockFixture()
        fixture.start()
        try:
            within_fixture = live_clock_probe.infer_clock_shift(ticks, epoch, **options)
            self.assertTrue(within_fixture.suitable_for_readonly_snapshot)
            self.assertEqual(within_fixture.observed_utc_epoch, epoch)
            missing = live_clock_probe.infer_clock_shift(
                ticks, epoch, require_host_trust=True, broker_server="Synthetic")
            self.assertFalse(missing.suitable_for_readonly_snapshot)
            self.assertEqual(missing.reason, "NO_TRUSTED_HOST_CLOCK")
        finally:
            fixture.stop()
        self.assertIs(live_clock_probe.infer_clock_shift, infer_clock_shift)
        self.assertEqual(infer_clock_shift(ticks, epoch, **options).reason, "FX_MARKET_CLOSED")


if __name__ == "__main__":
    unittest.main()
