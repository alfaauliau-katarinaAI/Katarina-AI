"""Scoped synthetic NTP fixture; never imported by production code."""
from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import patch

from katarina.intelligence.broker.broker_clock_alignment import HostClockTrust


class ModuleClockFixture:
    def start(self):
        def trust(*args, **kwargs):
            return HostClockTrust(True, "TRUSTED_HOST_NTP", "SYNTHETIC_TEST_ONLY",
                                  datetime.now(timezone.utc), 0.)
        self.stack = ExitStack()
        self.stack.enter_context(patch(
            "katarina.intelligence.cognition.observer.inspect_host_clock", side_effect=trust))

    def stop(self):
        self.stack.close()
