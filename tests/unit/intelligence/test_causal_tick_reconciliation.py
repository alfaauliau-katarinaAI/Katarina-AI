"""Native-brain BID/ASK reconciliation safety fixtures, not market alpha."""
import unittest
from katarina.intelligence.lab.causal_tick_reconciliation import (
    tick_reconcile,summarize_tick_reconciliation
)

SIGNAL={"symbol":"XAUUSD.vx","method":"TREND_PULLBACK",
    "side":"BUY","regime":"TREND_UP","signal_at":1800000000.,
    "sl":99.,"tp":102.}
BAR={"time":1800000000.+10800,"open":100.,"high":100.5,"low":99.5,"close":100.1}


def quotes():
    start=int(BAR["time"]*1000)
    return [(start,100.,100.1),(start+60000,100.5,100.6),
            (start+120000,99.5,99.6),(start+299000,100.1,100.2),
            (start+360000,102.5,102.6)]


class CausalTickReconciliationTests(unittest.TestCase):
    def run_quote(self, ticks=None, bar=None, signal=None, offset=3):
        return tick_reconcile(signal or SIGNAL,quotes() if ticks is None else ticks,
            BAR if bar is None else bar,raw_offset_hours=offset,
            tick_size=.01,extra_cost_r=.15)

    def test_positive_buy_quote_path_with_fee_assumption(self):
        value=self.run_quote()
        self.assertEqual(value["status"],"CLOSED_QUOTE_SIMULATION_ONLY")
        self.assertEqual(value["exit_reason"],"TP")
        self.assertEqual(value["fill_price_model"],102.)
        self.assertAlmostEqual(value["net_assumed_cost_r"],
                               (102-100.1)/(100.1-99.)-.15,places=5)
        self.assertFalse(value["broker_fills_verified"])
        self.assertFalse(value["real_commission_verified"])
        self.assertFalse(value["live_eligible"])

    def test_alignment_invalid_even_when_profits_look_positive(self):
        wrong=dict(BAR,high=101.)
        value=self.run_quote(bar=wrong)
        self.assertEqual(value["status"],"BID_TICK_BAR_ALIGNMENT_FAILED")
        self.assertNotIn("net_assumed_cost_r",value)

    def test_wrong_clock_offset_fails_closed(self):
        value=self.run_quote(offset=2)
        self.assertEqual(value["status"],"BROKER_CANDLE_CLOCK_OR_OHLC_MISMATCH")

    def test_buy_hit_stop_first_quote_uses_bid(self):
        v=quotes()
        v[-1]=(v[-1][0],98.,98.1)
        value=self.run_quote(ticks=v)
        self.assertEqual(value["exit_reason"],"SL")
        self.assertEqual(value["fill_price_model"],98.)
        self.assertLess(value["net_assumed_cost_r"],-1.)

    def test_sell_exits_on_ask_quote_not_bid(self):
        signal=dict(SIGNAL,side="SELL",sl=101.8,tp=98.)
        v=quotes()
        v[-1]=(v[-1][0],101.7,101.9)
        result=self.run_quote(ticks=v,signal=signal)
        self.assertEqual(result["exit_reason"],"SL")
        self.assertEqual(result["fill_price_model"],101.9)
        self.assertLess(result["net_assumed_cost_r"],-1.)

    def test_gap_is_not_reconstructed_with_future_profit(self):
        v=quotes()
        v[-1]=(v[-1][0]+600000,105.,105.1)
        result=self.run_quote(ticks=v)
        self.assertEqual(result["status"],"TICK_PATH_GAP")
        self.assertNotIn("net_assumed_cost_r",result)

    def test_numpy_mt5_structured_array_is_supported(self):
        import numpy as np
        data=np.array(quotes(),dtype=[("time_msc","i8"),("bid","f8"),("ask","f8")])
        value=self.run_quote(ticks=data)
        self.assertEqual(value["status"],"CLOSED_QUOTE_SIMULATION_ONLY")
        self.assertTrue(value["entry_m5_tick_bid_match"])

    def test_empty_quote_and_nonmonotonic_fail(self):
        self.assertEqual(self.run_quote(ticks=[])["status"],"NO_TICK_HISTORY")
        v=quotes()
        v[1]=(v[0][0]-2,100.5,100.6)
        self.assertEqual(self.run_quote(ticks=v)["status"],"TICKS_NOT_MONOTONIC")

    def test_corrupt_ask_and_untradeable_risk(self):
        v=quotes();v[-1]=(v[-1][0],102.5,102.0)
        self.assertEqual(self.run_quote(ticks=v)["status"],"BAD_BID_ASK_QUOTE")
        s=dict(SIGNAL,sl=100.09)
        self.assertEqual(self.run_quote(signal=s)["status"],"TICK_ENTRY_GEOMETRY_UNTRADEABLE")

    def test_non_quote_candidates_remain_in_denominator(self):
        good=self.run_quote()
        missing=self.run_quote(ticks=[])
        report=summarize_tick_reconciliation([
            {"signal":SIGNAL,"outcome":good},
            {"signal":SIGNAL,"outcome":missing}])
        self.assertEqual(report["quote_completed"],1)
        self.assertEqual(report["n_sampled"],2)
        self.assertEqual(report["reason_counts"]["NO_TICK_HISTORY"],1)
        self.assertEqual(report["cohorts"][0]["valid_quote_fraction"],.5)
        self.assertFalse(report["live_execution_authorized"])
        self.assertEqual(report["method_scorecard"][0]["sampled"],2)
        self.assertEqual(report["method_scorecard"][0]["verified_bidask_quote_paths"],1)
        self.assertEqual(report["method_scorecard"][0]["not_replayable"],1)
        self.assertEqual(report["monthly_scorecard"][0]["sampled"],2)
        self.assertEqual(report["monthly_symbol_method_scorecard"][0]["sampled"],2)
        self.assertTrue(report["this_is_ex_post_diagnosis_not_auto_strategy_training"])
        self.assertFalse(report["method_scorecard"][0]["authorizes_live_or_paper_promotion"])


if __name__=="__main__":
    unittest.main()
