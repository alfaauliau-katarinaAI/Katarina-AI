"""Research report must count all 17 symbols, both dates and all losses."""
import unittest
from datetime import datetime,timezone
from scripts.research.aggregate_closed_bar_forensics import aggregate

SYMS=[f"S{i:02d}.vx" for i in range(17)]
GROUPS=[SYMS[0:4],SYMS[4:8],SYMS[8:12],SYMS[12:17]]


def make_report(month,names):
    rows=[]
    for sym in names:
        t=int(datetime(2026,9 if month=="2026-09" else 10,20,
                       tzinfo=timezone.utc).timestamp())
        rows.append({
            "symbol":sym,"method":"RANGE_FADE","side":"SELL",
            "signal_month":month,"signal_epoch":t,
            "exit_reason":"STOP","is_loss":True,
            "net_proxy_r_assuming_0_15_extra_cost":-1.15,
            "both_stop_target_inside_one_M5_bar":False,
            "early_stop_first_15m":True,"holding_minutes":5,
            "pre_entry_spread_over_stop_risk":.38,
            "stop_distance_over_pre_entry_m15_atr":.8,
            "after_entry_unsequenced_M5_max_favorable_r":0.,
            "after_entry_unsequenced_M5_max_adverse_r":1.2,
        })
    return {
        "read_only":True,"orders_sent":0,"live_execution_authorized":False,
        "spread_source":"BROKER_M5_CLOSED_BAR_SPREAD_POINTS",
        "actual_historical_entry_bidask_verified":False,
        "symbols_requested":names,
        "counters":{"proxy_completed":len(rows),"evaluated":len(rows)*3,
                    "quote_path_unavailable":2,"technical_wait":len(rows)*2},
        "entry_failure_diagnostics":{
            "totals":{"n":len(rows)},
            "all_candidate_records":rows,
            "orders_sent":0,"live_execution_authorized":False,
        }
    }


def batches(month):
    return [make_report(month,g) for g in GROUPS]


class TestCombinedRootCauses(unittest.TestCase):
    def test_count_all_broker_symbols_losses_and_ambiguous_status(self):
        a=aggregate(batches("2026-09"),batches("2026-10"))
        self.assertEqual(a["all"]["n"],34)
        self.assertEqual(a["all"]["losses_after_assumed_cost"],34)
        self.assertEqual(a["all"]["exit_causes"]["STOP"],34)
        self.assertEqual(a["counters"]["evaluated"],102)
        self.assertEqual(a["counters"]["quote_path_unavailable"],16)
        self.assertEqual(len(a["instruments"]),17)
        self.assertEqual(a["number_of_negative_method_side_groups_in_both_windows"],1)
        self.assertFalse(a["live_execution_authorized"])
        self.assertTrue(a["profit_claims_and_live_promotion_forbidden"])

    def test_duplicate_symbol_in_same_month_rejected(self):
        a=batches("2026-09")
        a[1]["symbols_requested"]=[a[0]["symbols_requested"][0]]
        with self.assertRaises(ValueError):
            aggregate(a,batches("2026-10"))

    def test_cannot_hide_losing_label(self):
        a=batches("2026-09")
        a[0]["entry_failure_diagnostics"]["all_candidate_records"].pop()
        with self.assertRaisesRegex(ValueError,"outcomes"):
            aggregate(a,batches("2026-10"))

    def test_broker_order_provenance_cannot_be_mislabeled_as_research(self):
        a=batches("2026-09")
        a[0]["orders_sent"]=1
        with self.assertRaises(ValueError):
            aggregate(a,batches("2026-10"))


if __name__=="__main__":
    unittest.main()
