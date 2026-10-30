"""Scoped clock fixture for explicitly synthetic PC acceptance, never observe mode."""
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from katarina.intelligence.broker.broker_clock_alignment import HostClockTrust


@contextmanager
def synthetic_clock():
    def trust(*args, **kwargs):
        return HostClockTrust(True, "TRUSTED_HOST_NTP", "SYNTHETIC_TEST_ONLY",
                              datetime.now(timezone.utc), 0.)
    with patch("katarina.intelligence.cognition.observer.inspect_host_clock", side_effect=trust):
        yield
