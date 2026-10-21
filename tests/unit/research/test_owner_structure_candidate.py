"""Synthetic contract tests: NO claim of trading edge or live readiness."""
from dataclasses import replace
import unittest

from katarina.research.owner_structure_candidate import (
    StructuralCandidate, evaluate_structural_candidate,
)


class OwnerStructureCandidateTests(unittest.TestCase):
    def setUp(self):
        self.bull = StructuralCandidate(
            symbol="XAUUSD", side="BUY", evidence_sha256="a"*64,
            zone_born_ns=20, structure_break_closed_ns=610,
            signal_closed_ns=700, decision_ns=800,
            wave_pivot_times_ns=(100,200,300,400,500,600),
            wave_pivot_prices=(100.,110.,105.,122.,112.,128.),
            structure_break_level=110., structure_break_close=120.,
            zone_low=112., zone_high=116., zone_fresh=True,
            entry=114., stop_loss=108., target=130.,
            estimated_cost_price=.1,
        )

    def test_valid_bullish_geometry_is_only_research_eligible(self):
        r=evaluate_structural_candidate(self.bull)
        self.assertTrue(r.eligible_for_offline_research, r.blockers)
        self.assertEqual(r.blockers, ())
        self.assertFalse(r.live_execution_authorized)

    def test_valid_bearish_geometry_is_only_research_eligible(self):
        x=replace(self.bull,side="SELL",
                  wave_pivot_prices=tuple(300-v for v in self.bull.wave_pivot_prices),
                  structure_break_level=190.,structure_break_close=180.,
                  zone_low=184.,zone_high=188.,
                  entry=186.,stop_loss=192.,target=170.)
        r=evaluate_structural_candidate(x)
        self.assertTrue(r.eligible_for_offline_research,r.blockers)
        self.assertFalse(r.live_execution_authorized)

    def test_no_market_structure_break_is_rejected(self):
        r=evaluate_structural_candidate(replace(self.bull,structure_break_close=109.))
        self.assertIn("market_structure_break_unconfirmed",r.blockers)

    def test_old_mitigated_zone_is_rejected(self):
        r=evaluate_structural_candidate(replace(self.bull,zone_fresh=False))
        self.assertIn("supply_demand_zone_not_fresh",r.blockers)

    def test_entry_must_be_inside_zone(self):
        r=evaluate_structural_candidate(replace(self.bull,entry=125.))
        self.assertIn("entry_not_at_zone",r.blockers)

    def test_future_wave_pivot_is_rejected(self):
        x=replace(self.bull,wave_pivot_times_ns=(100,200,300,400,500,801))
        r=evaluate_structural_candidate(x)
        self.assertIn("wave_pivots_not_causal",r.blockers)

    def test_future_structure_break_is_rejected(self):
        r=evaluate_structural_candidate(replace(self.bull,structure_break_closed_ns=901))
        self.assertIn("causal_timestamps_invalid",r.blockers)

    def test_wave4_overlaps_wave1_is_rejected(self):
        x=replace(self.bull,wave_pivot_prices=(100.,110.,105.,122.,109.,128.))
        r=evaluate_structural_candidate(x)
        self.assertIn("elliott_impulse_hypothesis_unconfirmed",r.blockers)

    def test_stop_must_invalidate_trade(self):
        r=evaluate_structural_candidate(replace(self.bull,stop_loss=116.))
        self.assertIn("stop_or_target_on_wrong_side",r.blockers)

    def test_cost_adjusted_reward_must_be_sufficient(self):
        r=evaluate_structural_candidate(replace(self.bull,target=117.))
        self.assertIn("insufficient_cost_adjusted_reward",r.blockers)

    def test_missing_source_digest_is_rejected(self):
        r=evaluate_structural_candidate(replace(self.bull,evidence_sha256="trust-me"))
        self.assertIn("unverifiable_source_digest",r.blockers)

    def test_nan_and_wrong_price_types_are_rejected(self):
        for bad in (float("nan"),float("inf"),True):
            with self.subTest(bad=bad):
                r=evaluate_structural_candidate(replace(self.bull,entry=bad))
                self.assertIn("invalid_price_evidence",r.blockers)

    def test_no_pivots_does_not_crash_or_promote(self):
        r=evaluate_structural_candidate(replace(self.bull,wave_pivot_prices=None))
        self.assertFalse(r.eligible_for_offline_research)
        self.assertFalse(r.live_execution_authorized)

    def test_no_timestamp_tuple_does_not_crash(self):
        r=evaluate_structural_candidate(replace(self.bull,wave_pivot_times_ns=None))
        self.assertIn("wave_pivots_not_causal",r.blockers)


if __name__=="__main__":
    unittest.main()
