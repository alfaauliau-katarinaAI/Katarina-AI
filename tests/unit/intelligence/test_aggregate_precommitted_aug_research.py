"""Aggregate all frozen proposals and preserve missing broker tick quotes."""
import unittest
from katarina.intelligence.lab.precommitted_setup_research import (
    FROZEN_RULE_VERSION,
)
from scripts.research.aggregate_precommitted_aug_research import aggregate


SYMS=[f"TEST{i:02d}.vx" for i in range(17)]
GROUPS=[SYMS[:4],SYMS[4:8],SYMS[8:12],SYMS[12:]]


def mkbatch(symbols):
    xs=[]
    for symbol in symbols:
        xs.append({
            "symbol":symbol,"method":"RANGE_SWEEP_RECLAIM",
            "side":"SELL","signal_epoch":1786800000,
            "frozen_rule_version":FROZEN_RULE_VERSION,
        })
    outcomes=[{**x,"gross_proxy_r":-.8,
               "exit_reason":"STOP_FIRST_ASK_ESTIMATE_OHLC_PROXY"}
              for x in xs]
    audit=[{"signal":{"symbol":x["symbol"],"method":x["method"],
                       "side":x["side"],"signal_at":x["signal_epoch"]},
            "outcome":{"status":"BROKER_TICK_API_ERROR"}}
           for x in xs]
    return {
        "read_only":True,"orders_sent":0,"live_execution_authorized":False,
        "frozen_rule_version":FROZEN_RULE_VERSION,
        "actual_account_commission_schedule_verified":False,
        "real_entry_bidask_verified":False,
        "broker_symbols":symbols,
        "broker_data_coverage":{s:{"result":"AVAILABLE"} for s in symbols},
        "counters":{"market_clocks":100,
                    "censored_future_or_entry_geometry":0},
        "technical_proposals":len(xs),
        "all_proposals_frozen_before_future_outcome":xs,
        "simulated_outcomes":len(outcomes),
        "all_proxy_outcomes":outcomes,
        "tick_audit_records":audit,
    }


class TestFrozenAugAggregation(unittest.TestCase):
    def test_all_labels_and_failed_tick_paths_preserved(self):
        z=aggregate([mkbatch(s) for s in GROUPS])
        self.assertEqual(len(z["symbols"]),17)
        self.assertEqual(z["pre_outcome_proposals"],17)
        self.assertEqual(z["OHLC_completed_outcomes"],17)
        self.assertEqual(z["tick_audit_count"],17)
        self.assertEqual(z["tick_quote_complete"],0)
        self.assertEqual(z["tick_statuses"],{"BROKER_TICK_API_ERROR":17})
        self.assertAlmostEqual(z["all_proxy_0_15"]["mean_net_assumed_r"],-.95)
        self.assertFalse(z["live_execution_authorized"])

    def test_duplicate_broker_market_rejected(self):
        z=[mkbatch(s) for s in GROUPS]
        z[1]["broker_symbols"][0]=z[0]["broker_symbols"][0]
        with self.assertRaises(ValueError):aggregate(z)

    def test_invalid_commission_claim_rejected(self):
        z=[mkbatch(s) for s in GROUPS]
        z[0]["actual_account_commission_schedule_verified"]=True
        with self.assertRaises(ValueError):aggregate(z)

    def test_missing_frozen_signal_cannot_be_ignored(self):
        z=[mkbatch(s) for s in GROUPS]
        z[0]["all_proposals_frozen_before_future_outcome"].pop()
        with self.assertRaises(ValueError):aggregate(z)


if __name__=="__main__":unittest.main()
