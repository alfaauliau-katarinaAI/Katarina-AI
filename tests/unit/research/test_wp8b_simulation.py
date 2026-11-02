"""WP8b-B offline simulator/comparison regressions. Synthetic prices ONLY."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.research.setups.simulator import _exit, simulate, trade_to_dict, validate_registration
from katarina.research.validation import HypothesisRegistry, ValidationError, canonical, sha256_text
from scripts.research.compare_setups import compare_reports
from scripts.research.register_setup_hypothesis import register_setup

ZERO = datetime(2026, 1, 5, tzinfo=timezone.utc)
HID = "a" * 64


def bar(start, minutes, op, hi, lo, cl, spread=3):
    return {"time_utc": start.isoformat(),
            "closed_at_utc": (start + timedelta(minutes=minutes)).isoformat(),
            "open": op, "high": hi, "low": lo, "close": cl, "spread": spread,
            "tick_volume": 1, "real_volume": 0}


def dataset(side="BUY"):
    first = ZERO - timedelta(hours=4)
    vals = [100, 101, 102, 103] if side == "BUY" else [113, 112, 111, 110]
    h1 = [bar(first + timedelta(hours=i), 60, v, v+2, v-2, v)
          for i, v in enumerate(vals)]
    if side == "BUY":
        rows = [(101, 102, 100, 101), (102, 103, 101, 102),
                (103, 104, 102, 103), (104.5, 106, 104.1, 105.5),
                (105.2, 106, 104, 105.8), (105.8, 117, 99.5, 107),
                (107, 108, 106, 107)]
    else:
        rows = [(111, 113, 109, 110), (110, 112, 108, 109),
                (109, 111, 107, 108), (107, 107.5, 106.4, 106.5),
                (106.8, 108, 105, 106), (106, 115, 90, 100),
                (100, 101, 99, 100)]
    return {"M5": [bar(ZERO + timedelta(minutes=i*5), 5, *row) for i,row in enumerate(rows)],
            "H1": h1}


def spec(side):
    return {"name":"Synthetic market structure", "symbol":"XAUUSD",
            "side": side, "regime":"ANY", "playbook":"market_structure",
            "rules":"synthetic closed bar only", "parameters":{
                "lookback":3, "trend_lookback":3, "target_rr":2.0,
                "min_rr":1.5, "stop_buffer":.1, "breakout_buffer":.2,
                "max_hold_bars":3}}


class WP8bSimulationTest(unittest.TestCase):
    def test_buy_same_bar_collision_is_stop_first(self):
        trades = simulate(dataset(), spec("BUY"), HID, point=.01)
        self.assertEqual(len(trades),1)
        t = trades[0]
        self.assertEqual(t.side,"BUY")
        self.assertEqual(t.entry_at, ZERO+timedelta(minutes=20))
        self.assertEqual(t.entry_mid,105.2)
        self.assertLess(t.exit_mid,t.entry_mid)
        self.assertEqual(t.spread_entry,.03)
        self.assertEqual(t.spread_exit,.03)
        self.assertEqual(t.data_until,t.entry_at)
        self.assertEqual(t.trend_side,"BUY")
        self.assertEqual(trade_to_dict(t)["exit_at"],t.exit_at.isoformat())

    def test_sell_same_bar_collision_is_stop_first(self):
        trades = simulate(dataset("SELL"),spec("SELL"),HID,point=.01)
        self.assertEqual(len(trades),1)
        t=trades[0]
        self.assertGreater(t.exit_mid,t.entry_mid)
        self.assertEqual(t.trend_side,"SELL")

    def test_sell_stop_and_target_are_checked_at_ask_not_bid(self):
        """Bars are BID; a SELL closes at ASK = bid + spread * point."""
        rows = [bar(ZERO + timedelta(minutes=5*i), 5, 100.0, 100.95, 99.5, 100.0, spread=10)
                for i in range(3)]
        # bid high 100.95 < stop 101.0, but ask high = 100.95 + 10*0.01 = 101.05 >= stop
        self.assertEqual(_exit(rows, 0, 101.0, 98.0, "SELL", 3, .01), (0, 101.0))
        rows = [bar(ZERO + timedelta(minutes=5*i), 5, 100.0, 100.2, 98.0, 99.0, spread=10)
                for i in range(3)]
        # bid low 98.0 touches target 98.0, ask low 98.1 does not: no early SELL target
        self.assertEqual(_exit(rows, 0, 101.0, 98.0, "SELL", 3, .01), (2, 99.0))
        # BUY closes at bid: unchanged
        self.assertEqual(_exit(rows, 0, 97.0, 100.2, "BUY", 3, .01), (0, 100.2))

    def test_next_bar_open_is_real_entry_not_signal_close(self):
        t=simulate(dataset(),spec("BUY"),HID,point=.01)[0]
        self.assertNotEqual(t.entry_mid,dataset()["M5"][3]["close"])

    def test_future_price_mutation_cannot_change_closed_entry(self):
        bars=dataset()
        original=simulate(bars,spec("BUY"),HID,point=.01)
        bars["M5"].append(bar(ZERO+timedelta(minutes=35),5,300,400,200,350))
        again=simulate(bars,spec("BUY"),HID,point=.01)
        self.assertEqual(again[:len(original)],original)
        # Additional future bars may create NEW trades but must not revise old outcomes.

    def test_future_gap_drops_incomplete_outcome(self):
        bars=dataset()
        bars["M5"][5]["time_utc"]=(ZERO+timedelta(minutes=31)).isoformat()
        bars["M5"][5]["closed_at_utc"]=(ZERO+timedelta(minutes=36)).isoformat()
        bars["M5"][6]["time_utc"]=(ZERO+timedelta(minutes=36)).isoformat()
        bars["M5"][6]["closed_at_utc"]=(ZERO+timedelta(minutes=41)).isoformat()
        self.assertEqual(simulate(bars,spec("BUY"),HID,point=.01),[])

    def test_holdout_row_rejected(self):
        bars=dataset()
        bars["M5"].append(bar(datetime(2026,10,13,tzinfo=timezone.utc),5,100,101,99,100))
        with self.assertRaisesRegex(ValidationError,"holdout"):
            simulate(bars,spec("BUY"),HID,point=.01)

    def test_invalid_point_rejected(self):
        with self.assertRaises(ValidationError):
            simulate(dataset(),spec("BUY"),HID,point=0)

    def test_sixth_registration_refused_and_duplicate_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry=HypothesisRegistry(Path(tmp)/"registry.jsonl")
            first=None
            for i in range(5):
                x=spec("BUY")
                x["parameters"]["max_hold_bars"]=i+1
                entry=register_setup(registry,x,registered_utc=ZERO)
                first=first or x
            self.assertEqual(registry.trial_count(),5)
            self.assertEqual(register_setup(registry,first,registered_utc=ZERO)["hypothesis_id"],
                             registry.hypothesis_id(first))
            self.assertEqual(registry.trial_count(),5)
            extra=spec("BUY")
            extra["parameters"]["max_hold_bars"]=6
            with self.assertRaisesRegex(ValidationError,"too_many_hypotheses"):
                register_setup(registry,extra,registered_utc=ZERO)
            self.assertEqual(registry.trial_count(),5)

    def test_max_five_hypotheses_per_symbol_side(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry=HypothesisRegistry(Path(tmp)/"registry.jsonl")
            first=None
            for i in range(6):
                x=spec("BUY")
                x["parameters"]["max_hold_bars"]=i+1
                e=registry.register(x,registered_utc=ZERO)
                first=first or e["hypothesis_id"]
            with self.assertRaisesRegex(ValidationError,"too_many_hypotheses"):
                validate_registration(registry,first)


def report(hid, side="BUY", expectancy=.2):
    r={"tool":"katarina.research.validation","period":"DEVELOPMENT",
       "hypothesis_id":hid,"hypothesis":{"symbol":"XAUUSD","side":side,
                  "playbook":"market_structure","regime":"UPTREND"},
       "statistics":{"trades":3,"expectancy_r":expectancy,
                    "profit_factor":1.5,"win_rate":.66,"mean_cost_r":.05},
       "baselines":{"random_side_same_timing":{"expected_expectancy_r":0},
                    "trend_rule":{"expectancy_r":.02}},
       "weekly_block_bootstrap_lower_expectancy_r":-.1,
       "cost_sensitivity":{"net_expectancy_r_2_0x":.1},
       "verdict":"FAIL","trial_count":2,
       "live_execution_authorized":False}
    r["report_sha256"]=sha256_text(canonical(r))
    return r


class WP8bComparisonTest(unittest.TestCase):
    def test_deterministic_order_not_ranked_by_profit(self):
        a,b=report("a"*64,"SELL",9),report("b"*64,"BUY",-.2)
        self.assertEqual(compare_reports([a,b]),compare_reports([b,a]))
        self.assertEqual(compare_reports([a,b])["rows"][0]["side"],"BUY")

    def test_tamper_and_holdout_fail_closed(self):
        r=report(HID)
        r["statistics"]["expectancy_r"]=999
        with self.assertRaisesRegex(ValidationError,"hash"):
            compare_reports([r])
        r=report(HID)
        r["period"]="HOLDOUT"
        with self.assertRaises(ValidationError):
            compare_reports([r])

    def test_duplicate_reports_rejected(self):
        with self.assertRaisesRegex(ValidationError,"duplicate"):
            compare_reports([report(HID),report(HID)])


if __name__ == "__main__":
    unittest.main()
