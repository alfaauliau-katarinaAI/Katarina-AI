import unittest
from dataclasses import replace
from decimal import Decimal
from katarina.research.indicator_combinations import Observation, flags, screen, metrics, subset, choose

class IndicatorCombinationTests(unittest.TestCase):
    def rows(self):
        return [Observation(i*100, i*100+1, "BUY", Decimal(2 if i%3 else -1),
                            Decimal(1), {"adx": True, "fibonacci": True})
                for i in range(160)]

    def test_missing_features_are_unknown_not_pass(self):
        f = flags({"side":"BUY", "adx":"25", "fib_retrace":".5"})
        self.assertTrue(f["adx"])
        self.assertIsNone(f["adr"])
        self.assertIsNone(f["supply_demand"])

    def test_directional_supply_and_candles(self):
        row={"side":"SELL","supply_dist_atr":".2","demand_dist_atr":"3",
             "candle_pressure":"-.4","chart_breakout":"-1","candle_pattern":"-1"}
        f=flags(row)
        self.assertTrue(f["supply_demand"])
        self.assertTrue(f["candle_pressure"])
        self.assertTrue(f["candle_pattern"])
        self.assertTrue(f["chart_pattern"])

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            flags({"side":"BUY","adx":"nan"})

    def test_final_outcomes_cannot_change_selection(self):
        rows=self.rows()
        a=screen(rows)
        changed=[replace(r,pnl=Decimal(-1000)) if i>=120 else r for i,r in enumerate(rows)]
        b=screen(changed)
        self.assertEqual(a["sides"]["BUY"]["selected"], b["sides"]["BUY"]["selected"])
        self.assertTrue(a["sides"]["BUY"]["screen_pass"])
        self.assertFalse(b["sides"]["BUY"]["screen_pass"])
        self.assertFalse(a["strategy_validated"])

    def test_crossing_labels_purged(self):
        rows=self.rows()
        rows[119]=replace(rows[119],known=13000)
        result=screen(rows)
        self.assertEqual(result["purged_rows"],1)

    def test_duplicate_masks_removed(self):
        combo,detail=choose(self.rows(),"BUY")
        self.assertEqual(combo,["adx"])
        self.assertEqual(detail["nominal_combinations"],3)
        self.assertEqual(detail["unique_candidates"],1)
        self.assertEqual(detail["duplicate_masks_removed"],2)

    def test_small_sample_never_selected(self):
        combo,_=choose(self.rows()[:20],"BUY")
        self.assertIsNone(combo)

    def test_cost_stress_and_drawdown(self):
        rows=[Observation(i,i+1,"BUY",Decimal(x),Decimal(1),{}) for i,x in enumerate((2,-1,-2))]
        m=metrics(rows,.1)
        self.assertAlmostEqual(m["net_r"],-1.3)
        self.assertAlmostEqual(m["closed_trade_drawdown_r"],3.2)

    def test_unknown_filter_does_not_pass(self):
        self.assertEqual(subset(self.rows(),["adr"]),[])

    def test_invalid_risk_rejected_by_loader(self):
        import tempfile
        from pathlib import Path
        from katarina.research.indicator_combinations import load
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.csv"
            p.write_text("side;net_profit\nBUY;1\n")
            with self.assertRaises(ValueError):
                load(p,1,"1")
