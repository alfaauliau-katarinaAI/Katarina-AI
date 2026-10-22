"""WP11 clock inference when some broker markets are closed (synthetic data)."""
import unittest

from katarina.intelligence.broker.broker_clock_alignment import infer_clock_shift


class PartialMarketClockTests(unittest.TestCase):
    NOW = 1_800_000_000.
    SHIFT = 3 * 3600

    def quote(self, age=2, shift=SHIFT):
        return int(self.NOW + shift - age)

    def check(self, fresh, stale, wrong=0):
        ticks = {f"FX{i}": self.quote() for i in range(fresh)}
        ticks.update({f"CLOSED{i}": self.quote(age=3800) for i in range(stale)})
        ticks.update({f"WRONG{i}": self.quote(shift=2*3600) for i in range(wrong)})
        return infer_clock_shift(ticks, self.NOW)

    def test_three_fresh_two_closed_keep_verified_clock(self):
        finding = self.check(3, 2)
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.observed_hours_shift, 3)
        self.assertEqual(finding.samples_considered, 5)
        self.assertEqual(finding.confirming_symbols, 3)
        self.assertEqual(finding.confidence_fraction, 1.0)
        self.assertEqual(finding.stale_symbols, ("CLOSED0", "CLOSED1"))
        self.assertFalse(finding.live_execution_authorized)

    def test_three_fresh_four_closed_keep_verified_clock(self):
        finding = self.check(3, 4)
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.samples_considered, 7)
        self.assertEqual(finding.stale_symbols,
                         ("CLOSED0", "CLOSED1", "CLOSED2", "CLOSED3"))

    def test_two_fresh_three_closed_still_rejected(self):
        finding = self.check(2, 3)
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertIsNone(finding.observed_hours_shift)
        self.assertEqual(finding.stale_symbols, ("CLOSED0", "CLOSED1", "CLOSED2"))

    def test_three_versus_two_conflicting_fresh_shifts_rejected(self):
        finding = self.check(3, 0, 2)
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.confidence_fraction, 0.6)
        self.assertEqual(finding.stale_symbols, ())

    def test_three_correct_one_wrong_still_valid_at_seventy_five_percent(self):
        finding = self.check(3, 0, 1)
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.observed_hours_shift, 3)
        self.assertEqual(finding.confidence_fraction, 0.75)

    def test_out_of_range_offset_does_not_vote(self):
        ticks = {f"FX{i}": self.quote() for i in range(3)}
        ticks["BAD_HOUR"] = self.quote(shift=20*3600)
        finding = infer_clock_shift(ticks, self.NOW)
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.stale_symbols, ("BAD_HOUR",))


if __name__ == "__main__":
    unittest.main()
