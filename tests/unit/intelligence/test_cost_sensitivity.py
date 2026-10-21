import json
import tempfile
import unittest
from pathlib import Path
import sys

from katarina.intelligence.perception.cost_expectancy import hypothetical_trade_budget
SCRIPTS=Path(__file__).resolve().parents[3]/"scripts"/"research"
sys.path.insert(0,str(SCRIPTS))
from historical_cost_sensitivity import analyze,load


def shadow(side="BUY",ratio=.25):
    spread=.1
    bid,ask=100,100.1
    xbid,xask=100.3,100.4
    if side=="SELL":
        xbid,xask=99.5,99.6
    mid=(bid+ask)/2
    midpoint=((xbid+xask)/2-mid)*(1 if side=="BUY" else -1)
    mark=(xbid-ask if side=="BUY" else bid-xask)
    return dict(symbol="S",side=side,entry_bid=bid,entry_ask=ask,
        exit_bid=xbid,exit_ask=xask,entry_spread_atr=ratio,
        quoted_markout_bps=mark/mid*10000,
        midpoint_markout_bps=midpoint/mid*10000,
        cost_screen_pass=ratio<=.15,
        live_risk_authorized=False,is_realized_pnl=False,
        signal_bar_close_utc="2026-10-01T10:00:00+00:00")


def report(signals, version):
    return dict(report_version=version,live_execution_enabled=False,
         model_promotion_allowed=False,
         period=dict(start="2026-10-01",end_exclusive="2026-10-10"),
         signals_observed=len(signals),
         symbols=[dict(symbol="S",signals=signals)])


class BudgetTests(unittest.TestCase):
    def test_breakeven_hurdle_accounts_for_full_spread(self):
        a=hypothetical_trade_budget(
            spread=.25,target_distance=2,stop_distance=1,
            extra_roundtrip_cost=0,estimated_hit_probability=.45)
        self.assertAlmostEqual(a["breakeven_hit_probability"],1.25/3)
        self.assertAlmostEqual(a["conditional_net_reward_risk"],1.75/1.25)
        self.assertGreater(a["expectancy_price_units"],0)
        self.assertFalse(a["trade_approved"])
        self.assertFalse(a["model_promotion_allowed"])

    def test_missing_commission_or_hit_rate_fails_closed(self):
        a=hypothetical_trade_budget(
            spread=.25,target_distance=2,stop_distance=1)
        self.assertFalse(a["inputs_complete_for_hypothetical_expectancy"])
        self.assertIsNone(a["expectancy_price_units"])
        self.assertFalse(a["trade_approved"])
        b=hypothetical_trade_budget(
            spread=2.5,target_distance=2,stop_distance=1,
            extra_roundtrip_cost=0.1,estimated_hit_probability=.99)
        self.assertFalse(b["positive_target_after_known_cost"])
        self.assertIsNone(b["expectancy_price_units"])

    def test_extra_cost_raises_breakeven_hurdle(self):
        a=hypothetical_trade_budget(
            spread=.25,target_distance=2,stop_distance=1,
            extra_roundtrip_cost=0)
        b=hypothetical_trade_budget(
            spread=.25,target_distance=2,stop_distance=1,
            extra_roundtrip_cost=.2)
        self.assertGreater(b["breakeven_hit_probability"],
                           a["breakeven_hit_probability"])

    def test_invalid_prices_and_estimated_probability_rejected(self):
        for kw in (
            dict(spread=-1,target_distance=2,stop_distance=1),
            dict(spread=.1,target_distance=0,stop_distance=1),
            dict(spread=.1,target_distance=2,stop_distance=1,
                 estimated_hit_probability=1.1),
            dict(spread=.1,target_distance=2,stop_distance=1,
                 extra_roundtrip_cost=float("nan")),
        ):
            with self.assertRaises(ValueError):
                hypothetical_trade_budget(**kw)

    def test_fixed_counterfactual_threshold_grid_never_promotes(self):
        with tempfile.TemporaryDirectory() as directory:
            a=Path(directory)/"a.json"
            b=Path(directory)/"b.json"
            a.write_text(json.dumps(report([shadow(ratio=.15),
                          shadow(ratio=.25)],"historical_tick_shadow_v1")))
            b.write_text(json.dumps(report([shadow(ratio=.15)],
                          "historical_m5_m15_shadow_v1")))
            result=analyze({"M1_M5":[a],"M5_M15":[b]})
        rows=result["experiments"]["M1_M5"]["grid"]
        self.assertEqual(rows[0]["samples_after_cost_gate"],1)
        self.assertEqual(rows[1]["samples_after_cost_gate"],2)
        self.assertEqual(rows[-1]["samples_after_cost_gate"],2)
        self.assertFalse(result["automatic_gate_change_allowed"])
        self.assertFalse(result["model_promotion_allowed"])
        self.assertFalse(rows[1]["by_side"]["BUY"]["0.0"]["promotion_allowed"])
        self.assertAlmostEqual(rows[1]["by_side"]["BUY"]["2.0"]["mean_net_quote_bps"],
                               rows[1]["by_side"]["BUY"]["0.0"]["mean_net_quote_bps"]-2)

    def test_tampered_spread_gate_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"tampered.json"
            s=shadow(ratio=.25)
            s["cost_screen_pass"]=True
            path.write_text(json.dumps(report([s],"historical_tick_shadow_v1")))
            with self.assertRaisesRegex(ValueError,"gate_inconsistent"):
                load([path],"M1_M5")

    def test_net_quote_decomposition_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"tampered.json"
            s=shadow(ratio=.15)
            s["midpoint_markout_bps"]+=3
            path.write_text(json.dumps(report([s],"historical_tick_shadow_v1")))
            with self.assertRaisesRegex(ValueError,"spread_cost_decomposition_invalid"):
                load([path],"M1_M5")

    def test_duplicate_historical_window_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"a.json"
            path.write_text(json.dumps(report([shadow()],"historical_tick_shadow_v1")))
            with self.assertRaisesRegex(ValueError,"duplicate_window"):
                load([path,path],"M1_M5")


if __name__=="__main__":
    unittest.main()
