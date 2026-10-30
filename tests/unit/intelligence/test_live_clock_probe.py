"""Two-sample clock adversarial cases with synthetic timestamps only."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from katarina.intelligence.broker.broker_clock_alignment import HostClockTrust
from katarina.intelligence.broker.live_clock_probe import tick_sample, verify_live_feed_clock

NOW = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)
SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY")


class LiveClockProbeTests(unittest.TestCase):
    def evaluate(self, *, shift=2, frozen=False, state=None, advance=0, server="fixture", trust=True):
        now = NOW + timedelta(seconds=advance)
        stamp = int((now.timestamp() + shift*3600 - 2)*1000)
        second = {s: stamp for s in SYMBOLS}
        first = {s: stamp if frozen else stamp-200 for s in SYMBOLS}
        return verify_live_feed_clock(first, second,
            first_utc=now-timedelta(seconds=.2), second_utc=now,
            first_mono=10.+advance, second_mono=10.2+advance,
            host_trust=HostClockTrust(trust, "TRUSTED_HOST_NTP", "fixture",
                                     now-timedelta(seconds=30), .01),
            broker_server=server, state=state if state is not None else {})

    def test_progressing_ticks_and_trusted_host_verify_current_offset_only(self):
        finding, audit = self.evaluate()
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.observed_hours_shift, 2)
        self.assertEqual(audit["time_basis"], "LIVE_FEED_CLOCK")
        self.assertFalse(audit["historical_dst_verified"])
        self.assertFalse(audit["live_execution_authorized"])

    def test_three_frozen_ticks_at_wrong_whole_hour_do_not_verify(self):
        finding, audit = self.evaluate(shift=1, frozen=True)
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(audit["reason"], "STALE_QUOTES")

    def test_quiet_symbols_can_prove_progress_from_previous_cycle_without_fake_freshness(self):
        state = {}
        self.assertTrue(self.evaluate(state=state)[0].suitable_for_readonly_snapshot)
        finding, audit = self.evaluate(state=state, advance=60, frozen=True)
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(audit["progress_basis"], "PREVIOUS_CYCLE_SAME_SERVER")
        # Exactly the same old milliseconds do not pass in either sample window.
        now = NOW + timedelta(seconds=120)
        old = state["last_sample"]["ticks"]
        finding, _ = verify_live_feed_clock(old, old,
            first_utc=now-timedelta(seconds=.2), second_utc=now,
            first_mono=130., second_mono=130.2,
            host_trust=HostClockTrust(True,"TRUSTED_HOST_NTP","fixture",now,0.),
            broker_server="fixture", state=state)
        self.assertFalse(finding.suitable_for_readonly_snapshot)

    def test_missing_host_trust_never_falls_back_to_voting(self):
        finding, audit = self.evaluate(trust=False)
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(audit["reason"], "NO_TRUSTED_HOST_CLOCK")

    def test_offset_jump_near_dst_is_quarantined_and_needs_new_confirmation(self):
        state = {}
        self.assertTrue(self.evaluate(state=state)[0].suitable_for_readonly_snapshot)
        self.assertEqual(self.evaluate(shift=3,state=state,advance=1)[1]["reason"],
                         "QUARANTINED_UNEXPLAINED_SHIFT_JUMP")
        self.assertFalse(self.evaluate(shift=3,state=state,advance=2)[0].suitable_for_readonly_snapshot)
        finding, audit = self.evaluate(shift=3,state=state,advance=32)
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertTrue(audit["shift_reconfirmed_after_quarantine"])

    def test_broker_migration_does_not_reuse_earlier_broker_shift(self):
        state = {}
        self.evaluate(state=state)
        finding, _ = self.evaluate(shift=3, state=state, server="another-fixture")
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(state["shift"], 3)
        self.assertFalse(self.evaluate(server=None)[0].suitable_for_readonly_snapshot)

    def test_clock_step_between_samples_is_rejected(self):
        stamp = int((NOW.timestamp()+7200)*1000)
        finding, audit = verify_live_feed_clock(
            {s:stamp-1000 for s in SYMBOLS}, {s:stamp for s in SYMBOLS},
            first_utc=NOW-timedelta(hours=1), second_utc=NOW,
            first_mono=10., second_mono=10.2, host_trust=None,
            broker_server="fixture", state={})
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(audit["reason"], "HOST_UTC_STEP_DETECTED")

    def test_tick_milliseconds_and_prices_must_be_real_and_consistent(self):
        good = SimpleNamespace(time=100, time_msc=100001, bid=1., ask=1.1)
        self.assertEqual(tick_sample({"FX":good}), {"FX":100001})
        for tick in (SimpleNamespace(time=100,bid=1.,ask=1.1),
                     SimpleNamespace(time=100,time_msc=101001,bid=1.,ask=1.1),
                     SimpleNamespace(time=100,time_msc=100001,bid=float("nan"),ask=1.1)):
            self.assertEqual(tick_sample({"FX":tick}), {})
