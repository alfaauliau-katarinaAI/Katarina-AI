"""Daily session pauses no longer discard research trades; weekends still do."""
import unittest

from katarina.intelligence.autonomous_research import evaluate
from katarina.intelligence.session_gaps import MAX_SESSION_GAP_SECONDS, spans_long_gap

H = 3600
MONDAY = 1_704_067_200 + H  # 2024-01-01 01:00 UTC, a Monday


def gold_like_stamps(weeks):
    """23 H1 bars per weekday (one-hour daily pause), closed Saturday and Sunday."""
    stamps = []
    for week in range(weeks):
        for day in range(5):
            start = MONDAY + (week * 7 + day) * 24 * H
            stamps.extend(start + h * H for h in range(23))
    return stamps


def bars(stamps):
    rows = []
    for n, stamp in enumerate(stamps):
        close = 100 + (n % 37) * .3 + (n // 37) * .05
        rows.append([stamp, close - .1, close + 1, close - 1, close])
    return rows


class SpansLongGapTest(unittest.TestCase):
    def test_daily_pause_is_allowed(self):
        rows = [[0], [H], [3 * H], [4 * H]]  # one missing bar = 2 h step
        self.assertFalse(spans_long_gap(rows, 0, 3))

    def test_weekend_is_excluded(self):
        rows = [[0], [H], [H + 48 * H]]
        self.assertTrue(spans_long_gap(rows, 0, 2))

    def test_gap_just_over_limit_is_excluded(self):
        rows = [[0], [MAX_SESSION_GAP_SECONDS + H]]
        self.assertTrue(spans_long_gap(rows, 0, 1))

    def test_gold_like_schedule_keeps_most_24_bar_windows(self):
        rows = [[s] for s in gold_like_stamps(8)]
        windows = range(0, len(rows) - 24)
        exact_hour = sum(all(rows[j + 1][0] - rows[j][0] == H for j in range(i, i + 24)) for i in windows)
        allowed = sum(not spans_long_gap(rows, i, 24) for i in windows)
        self.assertEqual(exact_hour, 0)  # the old rule kept no 24-bar trade at all
        self.assertGreater(allowed, len(windows) * .7)  # only windows touching a weekend drop


class EvaluateSampleCountTest(unittest.TestCase):
    def test_h24_research_gets_samples_on_gold_like_schedule(self):
        rows = bars(gold_like_stamps(40))
        result = evaluate(rows, ('MOMENTUM', 1, 24, 24, .5), spread=.05)
        self.assertGreater(result['development']['n'] + result['review']['n'], 0)
        self.assertEqual(result['gap_policy'], 'H1_ALLOW_DAILY_PAUSE_UP_TO_4H')


if __name__ == '__main__':
    unittest.main()
