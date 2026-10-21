import unittest
from dataclasses import replace
from katarina.intelligence.strategy_selector import StrategySelectionBrain,StrategyObservation
D=86_400_000_000_000

class SelectorTests(unittest.TestCase):
    def rows(self):
        out=[]
        for day in list(range(1,61))+list(range(71,131)):
            value=3. if day%5 in (0,1) else -1.
            out.append(StrategyObservation(str(day),"pullback_BUY","BUY","UP",day*D,day*D+1,value))
        return out
    def fit(self,rows=None):
        s=StrategySelectionBrain()
        evidence=s.fit(self.rows() if rows is None else rows,train_cutoff_ns=70*D,selection_end_ns=140*D)
        return s,evidence
    def test_positive_expectancy_below_55_percent_wins(self):
        s,e=self.fit()
        self.assertEqual(s.recommend("BUY","UP")["candidate"],"pullback_BUY")
        self.assertLess(e["choices"][0]["selection"]["win_rate"],.55)
        self.assertFalse(s.recommend("BUY","UP")["live_risk_authorized"])
    def test_unseen_side_regime_returns_no_trade(self):
        s,_=self.fit()
        for side,regime in (("SELL","UP"),("BUY","DOWN"),("BUY","UNKNOWN")):
            self.assertEqual(s.recommend(side,regime)["action"],"NO_TRADE")
    def test_final_outcomes_cannot_affect_choice(self):
        rows=self.rows()
        future=[replace(rows[0],sample_id="future",entry_ns=141*D,known_ns=142*D,net_r=999)]
        _,a=self.fit(rows+future)
        _,b=self.fit(rows+[replace(future[0],net_r=-999)])
        self.assertEqual(a["policy_sha256"],b["policy_sha256"])
    def test_crossing_training_labels_purged(self):
        rows=self.rows()
        rows[0]=replace(rows[0],known_ns=71*D)
        _,e=self.fit(rows)
        self.assertEqual(e["diagnostics"][0]["train"]["trades"],59)
    def test_negative_expected_value_not_selected(self):
        s,_=self.fit([replace(r,net_r=-1) for r in self.rows()])
        self.assertEqual(s.recommend("BUY","UP")["action"],"NO_TRADE")
    def test_duplicate_observations_rejected(self):
        rows=self.rows()
        with self.assertRaises(ValueError): self.fit(rows+[rows[0]])
    def test_nonfinite_observation_rejected(self):
        with self.assertRaises(ValueError): replace(self.rows()[0],net_r=float("nan"))
    def test_final_cannot_overlap_development(self):
        s,_=self.fit()
        with self.assertRaises(ValueError): s.audit_final([],final_start_ns=100*D,final_end_ns=160*D)
    def test_empty_final_is_rejected(self):
        s,_=self.fit()
        report=s.audit_final([],final_start_ns=140*D,final_end_ns=160*D)
        self.assertEqual(report["cells"][0]["result"],"REJECTED")
        self.assertFalse(report["validated_strategy"])
