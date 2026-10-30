# Package marker for KATARINA staged implementation tests.
from datetime import datetime, timezone
from katarina.intelligence.broker.broker_clock_alignment import (
    HostClockTrust, set_host_clock_provider,
)

# Set mock host clock provider for synthetic integration test suites on CI runners
set_host_clock_provider(lambda now: HostClockTrust(
    trusted=True,
    time_basis="TRUSTED_HOST_NTP",
    reason="NTP_SYNCHRONIZED",
    last_sync_utc=now or datetime.now(timezone.utc),
    skew_seconds=0.0,
))
