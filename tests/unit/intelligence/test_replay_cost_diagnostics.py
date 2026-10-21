"""Frozen cost-grid tests: must never hide losers or authorize live alpha."""
import unittest
from katarina.intelligence.lab.adaptive_walkforward import PaperEvent
from katarina.intelligence.lab.replay_cost_diagnostics import describe_candidates


def entry(t,r,method="TREND_PULLBACK"):
    return {
        "symbol":"XAUUSD.vx","method":method,"side":"BUY",
        "signal_at":t,"label_known_at":t+1800,
        "proxy_gross_r":r,"regime":"TREND_UP"
    }


def ev(x):
    return PaperEvent(x["symbol"],x["method"],x["side"],
        x["signal_at"],x["label_known_at"],x["proxy_gross_r"],
        .7,.04,market_regime=x["regime"])


class ReplayCostDiagnosticsTests(unittest.TestCase):
    def test_cost_grid_includes_loss_and_purged_case(self):
        first=entry(1790000000,2.0)
        second=entry(1790003600,-1.0)
        third=entry(1790007200,-1.0)
        s=describe_candidates(
            [first,second,third],
            {"train":[ev(first)],"validation":[ev(second)],"test":[]})
        self.assertEqual(s["candidate_total"],3)
        c=s["cohorts"][0]
        self.assertEqual(c["split_counts"]["purged_overlap_or_insufficient"],1)
        self.assertEqual(c["split_counts"]["validation"],1)
        self.assertAlmostEqual(
            c["cost_scenarios_r"]["0.15"]["mean_net_proxy_r"],
            -0.15,places=6)
        self.assertFalse(c["eligible_for_live"])
        self.assertFalse(s["validated_live_edge"])

    def test_duplicate_signal_in_two_partitions_fails(self):
        a=entry(1790000000,2)
        with self.assertRaises(ValueError):
            describe_candidates([a],{"train":[ev(a)],"test":[ev(a)]})

    def test_invalid_costs_and_empty_data(self):
        with self.assertRaises(ValueError):
            describe_candidates([],{},costs=(-.01,))
        self.assertEqual(describe_candidates([],{"train":[]})["candidate_total"],0)


if __name__=="__main__":unittest.main()
