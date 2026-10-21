"""Offline causal candidate research gate does not authorize broker trades."""
import unittest
from katarina.intelligence.lab.research_signal_ablation import eligible_for_research as pass_gate


class ResearchSignalAblationTests(unittest.TestCase):
    def test_default_preserves_all_valid_candidates(self):
        self.assertTrue(pass_gate(.62,"BUY"))
        self.assertTrue(pass_gate(.63,"SELL"))

    def test_high_confidence_side_filter_before_future_r(self):
        self.assertTrue(pass_gate(.8,"SELL",minimum_score=.8,research_side="SELL"))
        self.assertFalse(pass_gate(.79,"SELL",minimum_score=.8,research_side="SELL"))
        self.assertFalse(pass_gate(.9,"BUY",minimum_score=.8,research_side="SELL"))
        self.assertTrue(pass_gate(.9,"BUY",minimum_score=.8,research_side="BUY"))

    def test_invalid_and_future_like_data_do_not_pass_silently(self):
        for score in (float("nan"), float("inf"), -1, 1.1, True):
            with self.assertRaises(ValueError):
                pass_gate(score,"BUY")
        for side in ("WAIT","UNKNOWN",""):
            with self.assertRaises(ValueError):
                pass_gate(.9,side)
        with self.assertRaises(ValueError):
            pass_gate(.9,"SELL",minimum_score=float("nan"))
        with self.assertRaises(ValueError):
            pass_gate(.9,"SELL",research_side="LONG")


if __name__=="__main__":
    unittest.main()
