"""STAGE1-PREFLIGHT: leakage-guard reasons of research/validation.py that had no literal test.

Synthetic trades exercise the TOOL only; nothing here is trading evidence.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
import unittest

from katarina.research import validation as v

UTC = timezone.utc
SPLIT = v.DataSplit(datetime(2026, 1, 5, tzinfo=UTC), datetime(2026, 7, 6, tzinfo=UTC),
                    datetime(2026, 7, 6, tzinfo=UTC), datetime(2027, 1, 4, tzinfo=UTC))
ENTRY = datetime(2026, 2, 2, 8, tzinfo=UTC)


def trade(trade_id="a", entry=ENTRY, hours=2, **changes):
    base = v.Trade(trade_id=trade_id, side="BUY", entry_at=entry, exit_at=entry + timedelta(hours=hours),
                   known_at=entry + timedelta(hours=hours), data_until=entry - timedelta(seconds=1),
                   entry_mid=2000.0, exit_mid=2010.0, stop_distance=10.0, spread_entry=.3, spread_exit=.3,
                   trend_side="BUY")
    return replace(base, **changes)


def rejected(*rows):
    return v.guard_trades(list(rows), SPLIT, "DEVELOPMENT")[1]


class LeakageGuardCodes(unittest.TestCase):
    def test_duplicate_or_empty_trade_id(self):
        self.assertEqual(rejected(trade("a"), trade("a", entry=ENTRY + timedelta(days=1))),
                         [("a", "DUPLICATE_OR_EMPTY_ID")])
        self.assertEqual(rejected(trade("")), [("", "DUPLICATE_OR_EMPTY_ID")])

    def test_invalid_prices_stop_and_spread(self):
        for changes in ({"entry_mid": math.nan}, {"exit_mid": math.inf}, {"stop_distance": 0.0},
                        {"stop_distance": -1.0}, {"spread_entry": -0.1}, {"spread_exit": -0.1}):
            with self.subTest(changes=changes):
                self.assertEqual(rejected(trade(**changes)), [("a", "INVALID_PRICES")])

    def test_overlapping_positions_cannot_both_count(self):
        first = trade("a", hours=3)
        second = trade("b", entry=ENTRY + timedelta(hours=1))  # opened while "a" is still open
        accepted, refused = v.guard_trades([second, first], SPLIT, "DEVELOPMENT")
        self.assertEqual([t.trade_id for t in accepted], ["a"])
        self.assertEqual(refused, [("b", "OVERLAPPING_POSITION")])
        later = trade("c", entry=ENTRY + timedelta(hours=3))  # starts exactly at the previous exit
        self.assertEqual(rejected(first, later), [])

    def test_development_trade_may_not_end_inside_the_holdout(self):
        edge = datetime(2026, 7, 5, 22, tzinfo=UTC)
        self.assertEqual(rejected(trade("x", entry=edge, hours=4)), [("x", "CROSSES_PERIOD_END")])


if __name__ == "__main__":
    unittest.main()
