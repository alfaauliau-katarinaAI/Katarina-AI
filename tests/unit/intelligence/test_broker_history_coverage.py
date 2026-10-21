"""Non-authorizing broker deals diagnostics; historical balance != full risk."""
import unittest
from datetime import datetime,timezone
from types import SimpleNamespace
from katarina.intelligence.broker.broker_history_coverage import (
    analyze_deal_coverage,inspect_history,
)

NOW=datetime(2026,10,15,9,tzinfo=timezone.utc)

def deal(entry,*,kind=0,profit=0.,commission=0.,swap=0.,fee=0.):
    return SimpleNamespace(type=kind,entry=entry,profit=profit,
                           commission=commission,swap=swap,fee=fee,
                           login=55555,ticket=12345)

class BrokerHistoryCoverageTests(unittest.TestCase):
    def test_observed_real_deals_cannot_claim_total_risk(self):
        trades=[deal(0,commission=-.1),deal(1,profit=5.),
                deal(1,kind=1,profit=-3.,commission=-.3,fee=-.05)]
        state=analyze_deal_coverage(trades,current_balance=1000.)
        self.assertEqual(state["status"],"DEAL_FIELDS_OBSERVED_NOT_FULL_RISK_LEDGER")
        self.assertEqual(state["deal_count"],3)
        self.assertEqual(state["entry_deal_count"],1)
        self.assertEqual(state["exit_deal_count"],2)
        self.assertEqual(state["commission_nonzero_samples"],2)
        self.assertEqual(state["net_realized_ratio_to_current_balance"],.00155)
        self.assertFalse(state["historical_range_complete"])
        self.assertFalse(state["live_execution_authorized"])
        self.assertFalse(state["realized_daily_loss_verified"])
        for field in ("login","ticket","account","balance","equity"):
            self.assertNotIn(field,state)

    def test_deposits_are_not_trades(self):
        state=analyze_deal_coverage([deal(0,kind=2,profit=100000)],
                                    current_balance=1000.)
        self.assertEqual(state["deal_count"],0)
        self.assertEqual(state["net_realized_ratio_to_current_balance"],0)

    def test_missing_or_invalid_history_refuses_fabricated_zero(self):
        self.assertIsNone(analyze_deal_coverage(None,current_balance=1000.)
                          ["deal_count"])
        self.assertEqual(
            analyze_deal_coverage([deal(1,profit=float("nan"))],
                                  current_balance=1000.)["status"],
            "MALFORMED_DEAL_HISTORY")
        self.assertEqual(
            analyze_deal_coverage([],current_balance=0)["status"],
            "ACCOUNT_BALANCE_UNAVAILABLE")

    def test_wrapper_is_read_only_and_handles_broker_outage(self):
        class Broker:
            def account_info(self):return SimpleNamespace(balance=250.)
            def history_deals_get(self,start,end):
                self.start=start;self.end=end
                return (deal(0),deal(1,profit=-1))
        b=Broker()
        value=inspect_history(b,as_of_utc=NOW)
        self.assertEqual(value["exit_deal_count"],1)
        self.assertEqual((b.end-b.start).total_seconds(),7*86400)
        self.assertEqual(value["net_realized_ratio_to_current_balance"],-.004)
        with self.assertRaises(ValueError):
            inspect_history(b,as_of_utc=datetime(2026,10,15))
        with self.assertRaises(ValueError):
            inspect_history(b,as_of_utc=NOW,period_hours=0)

    def test_none_trade_info_never_authorizes_execution(self):
        data=analyze_deal_coverage([deal(0,kind=0)],current_balance=1000)
        self.assertEqual(data["exit_deal_count"],0)
        self.assertFalse(data["strategy_specific_costs_verified"])
        self.assertFalse(data["independent_execution_slippage_verified"])

if __name__=="__main__":
    unittest.main()
