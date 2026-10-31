"""Scoped synthetic NTP fixture; never imported by production code."""
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from katarina.intelligence.broker.broker_clock_alignment import (
    HostClockTrust,
    infer_clock_shift as _real_infer_clock_shift,
)


def synthetic_infer_clock_shift(ticks, observed_utc_epoch, **kwargs):
    """Translate synthetic clocks to a trading weekday, then run real strict checks.

    Only scoped fixture-bound calls shift; production market-closed behavior,
    stale host NTP and missing tick evidence remain fail-closed.
    """
    observed = datetime.fromtimestamp(observed_utc_epoch, timezone.utc)
    closed = (observed.weekday() == 4 and observed.hour >= 20 or
              observed.weekday() == 5 or
              observed.weekday() == 6 and observed.hour < 21)
    if not closed:
        return _real_infer_clock_shift(ticks, observed_utc_epoch, **kwargs)
    seconds = (observed.weekday() - 3) * 86400
    trust = kwargs.get("host_trust")
    if isinstance(trust, HostClockTrust):
        delta = timedelta(seconds=seconds)
        kwargs["host_trust"] = replace(
            trust,
            last_sync_utc=trust.last_sync_utc - delta if trust.last_sync_utc else None,
            observed_at_utc=trust.observed_at_utc - delta if trust.observed_at_utc else None,
        )
    outcome = _real_infer_clock_shift(
        {symbol: epoch - seconds for symbol, epoch in ticks.items()},
        observed_utc_epoch - seconds, **kwargs)
    return replace(outcome, observed_utc_epoch=observed_utc_epoch)


class ModuleClockFixture:
    def start(self):
        def trust(*args, **kwargs):
            return HostClockTrust(True, "TRUSTED_HOST_NTP", "SYNTHETIC_TEST_ONLY",
                                  datetime.now(timezone.utc), 0.)
        self.stack = ExitStack()
        self.stack.enter_context(patch(
            "katarina.intelligence.cognition.observer.inspect_host_clock", side_effect=trust))
        self.stack.enter_context(patch(
            "katarina.intelligence.broker.live_clock_probe.infer_clock_shift",
            side_effect=synthetic_infer_clock_shift))

    def stop(self):
        self.stack.close()
