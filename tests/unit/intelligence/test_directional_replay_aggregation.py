"""Prevent multi-pair metric inflation and duplicate historical samples."""
import unittest
from scripts.research.aggregate_directional_brain_replay import aggregate_batches


def report(symbol,n,net):
    return {
        "read_only":True,"live_execution_authorized":False,"orders_sent":0,
        "spread_source":"BROKER_M5_CLOSED_BAR_SPREAD_POINTS",
        "actual_historical_entry_bidask_verified":False,
        "retrospective_data_already_inspected_not_independent_holdout":True,
        "symbols_requested":[symbol],
        "counters":{"evaluated":n*8,"proxy_completed":n,
                    "technical_wait":n*3},
        "purged_calendar_split_counts":{"train":n,"validation":0,
            "test":0,"purged_or_embargoed":0},
        "adapted_replay":{"adaptive":{"trades":0,"wait_events":n}},
        "full_cost_sensitivity":{
            "candidate_total":n,
            "cohorts":[{
                "symbol":symbol,"method":"RANGE_FADE","side":"SELL",
                "all_attempts_including_blocked":n,
                "cost_scenarios_r":{
                    str(cost):{"mean_net_proxy_r":net-cost}
                    for cost in (.05,.15,.30)
                },
            }]
        },
    }


class TestAggregateReadOnlyBatches(unittest.TestCase):
    def test_two_symbol_outcomes_weighted_and_no_broker_edge_claim(self):
        a=aggregate_batches([report("EURUSD.vx",3,-.3),
                             report("XAUUSD.vx",2,.2)])
        self.assertEqual(a["symbol_count"],2)
        self.assertEqual(a["counters"]["evaluated"],40)
        self.assertEqual(a["counters"]["proxy_completed"],5)
        self.assertEqual(a["counters"]["adaptive_selected"],0)
        self.assertEqual(len(a["method_side_scorecard"]),1)
        group=a["method_side_scorecard"][0]
        self.assertEqual(group["n"],5)
        self.assertAlmostEqual(
            group["mean_modeled_net_r_by_cost"]["0.15"],-.25)
        self.assertFalse(a["true_17_symbol_combined_portfolio_PF_or_drawdown_available"])
        self.assertFalse(a["live_execution_authorized"])
        self.assertEqual(a["research_action"],"WAIT")
        self.assertEqual(a["orders_sent"],0)

    def test_duplicate_pair_rejected(self):
        with self.assertRaisesRegex(ValueError,"duplicate"):
            aggregate_batches([report("EURUSD.vx",3,.2),
                               report("EURUSD.vx",2,.1)])

    def test_invalid_provenance_cannot_promote_live(self):
        bad=report("EURUSD.vx",3,.3)
        bad["live_execution_authorized"]=True
        with self.assertRaisesRegex(ValueError,"untrusted"):
            aggregate_batches([bad])

    def test_missing_cost_or_inconsistent_total_fails(self):
        bad=report("EURUSD.vx",3,.3)
        bad["full_cost_sensitivity"]["cohorts"][0]["cost_scenarios_r"].pop("0.15")
        with self.assertRaises(ValueError):aggregate_batches([bad])
        bad=report("EURUSD.vx",3,.3)
        bad["full_cost_sensitivity"]["candidate_total"]=2
        with self.assertRaises(ValueError):aggregate_batches([bad])


if __name__=="__main__":unittest.main()
