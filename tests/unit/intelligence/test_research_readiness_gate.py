"""No strategy promotion based solely on historically attractive samples."""
import unittest
from dataclasses import replace
from katarina.intelligence.lab.research_readiness_gate import Evidence,evaluate_readiness

class TestReadiness(unittest.TestCase):
    def setUp(self):
        self.x=Evidence("US30.vx",300,.15,1.30,.07,(.1,.1,.1))
    def test_historical_good_backtest_is_unvalidated(self):
        v=evaluate_readiness(self.x)
        self.assertEqual(v.status,"UNVALIDATED")
        self.assertIn("historical_period_previously_inspected",v.reasons)
        self.assertFalse(v.candidate_for_paper)
        self.assertFalse(v.live_execution_authorized)
    def test_paper_candidate_requires_all_independent_evidence(self):
        x=replace(self.x,unseen_holdout=True,
                  broker_costs_reconciled=True,
                  historical_news_verified=True,
                  full_chronological_replay=True,
                  causal_inputs_verified=True)
        v=evaluate_readiness(x)
        self.assertEqual(v.status,"PAPER_RESEARCH_CANDIDATE")
        self.assertTrue(v.candidate_for_paper)
        self.assertFalse(v.live_execution_authorized)
    def test_cost_stress_veto(self):
        x=replace(self.x,cost_stress_mean_r=-.01)
        self.assertIn("edge_disappears_under_cost_stress",
                      evaluate_readiness(x).reasons)
    def test_historical_segment_instability_veto(self):
        x=replace(self.x,segment_mean_r=(-.05,.25,.2))
        self.assertIn("unstable_chronological_segments",
                      evaluate_readiness(x).reasons)
    def test_small_sample_veto(self):
        x=replace(self.x,trades=9)
        self.assertIn("not_enough_observations",
                      evaluate_readiness(x).reasons)
    def test_spoofed_evidence_flags_cannot_promote_research(self):
        valid=replace(self.x,unseen_holdout=True,
                      broker_costs_reconciled=True,
                      historical_news_verified=True,
                      full_chronological_replay=True,
                      causal_inputs_verified=True)
        for key in ("unseen_holdout","broker_costs_reconciled",
                    "historical_news_verified","full_chronological_replay",
                    "causal_inputs_verified"):
            for spoof in ("true","False",1,None):
                with self.subTest(field=key,value=spoof):
                    out=evaluate_readiness(replace(valid,**{key:spoof}))
                    self.assertFalse(out.candidate_for_paper)
                    self.assertFalse(out.live_execution_authorized)

    def test_invalid_metric_and_type_are_never_treated_as_positive_edge(self):
        for changed in (
            {"symbol":None},{"symbol":"  "},
            {"trades":True},{"trades":"300"},
            {"mean_r":"0.15"},{"profit_factor":True},
            {"cost_stress_mean_r":float("inf")},
            {"segment_mean_r":(0.1,"0.2",0.3)},
            {"segment_mean_r":None},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises((ValueError,TypeError)):
                    evaluate_readiness(replace(self.x,**changed))

    def test_bad_numbers(self):
        with self.assertRaises(ValueError):
            evaluate_readiness(replace(self.x,mean_r=float("nan")))
        with self.assertRaises(ValueError):
            evaluate_readiness(replace(self.x,trades=-1))
if __name__=="__main__":unittest.main()