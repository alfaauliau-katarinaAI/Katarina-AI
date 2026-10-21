"""Which H1 bar gaps a research trade may span.

Gold, indices and many CFDs pause for about an hour every trading day, so the
next H1 bar after the pause is 7200 s (sometimes 10800 s) later. Requiring
every step to be exactly 3600 s discarded nearly every 12- and 24-bar trade on
those instruments. Short daily pauses are now allowed; weekends, holidays and
other long outages are still excluded because their price gap is not a normal
holding risk for these experiments.
"""

H1_SECONDS = 3600
# Daily maintenance/rollover pauses are 1-2 h on common brokers; 4 h leaves
# margin while every weekend (about 48 h) and holiday stays excluded.
MAX_SESSION_GAP_SECONDS = 4 * 3600
GAP_POLICY = 'H1_ALLOW_DAILY_PAUSE_UP_TO_4H'


def spans_long_gap(rows, start, horizon):
    """True when bars start..start+horizon cross a gap that is not a short daily pause."""
    return any(not H1_SECONDS <= rows[j + 1][0] - rows[j][0] <= MAX_SESSION_GAP_SECONDS
               for j in range(start, start + horizon))
