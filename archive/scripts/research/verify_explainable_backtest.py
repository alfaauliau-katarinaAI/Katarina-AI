"""Safety invariants for historical shadow-signal fills; run on Windows MT5 Python."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from backtest_explainable_55_pairs import hypothetic_fill, bisected_indices

class ExecutionModels(unittest.TestCase):
    def bars(self):
        dtype=[("time","<i8"),("open","<f8"),("high","<f8"),
               ("low","<f8"),("close","<f8"),("spread","<i4")]
        b=np.zeros(100,dtype=dtype)
        b["time"]=1750000000+np.arange(100)*300
        b["open"]=100;b["high"]=100.4;b["low"]=99.6
        b["close"]=100;b["spread"]=2
        return b
    def test_sl_precedes_tp_both_directions(self):
        for side in (1,-1):
            b=self.bars()
            b["high"][26]=105;b["low"][26]=95
            x=hypothetic_fill(b,25,side,.01,1.)
            self.assertEqual(x["result"],"SL")
            self.assertEqual(x["exit_idx"],26)
            self.assertAlmostEqual(x["R"],-1.03)
    def test_tp_is_hit_only_after_entry(self):
        b=self.bars()
        b["high"][25]=110  # signal bar must NOT be used to fill
        b["high"][26]=103;b["low"][26]=100
        x=hypothetic_fill(b,25,1,.01,1.)
        self.assertEqual(x["result"],"TP")
        self.assertEqual(x["exit_idx"],26)
        self.assertAlmostEqual(x["R"],1.77)
    def test_no_gap_in_entered_bar(self):
        b=self.bars();b["time"][26]+=600
        self.assertIsNone(hypothetic_fill(b,25,1,.01,1.))
    def test_higher_timeframe_not_future(self):
        times=np.array([0,900,1800,2700],dtype=np.int64)
        self.assertEqual(bisected_indices(times,1800,900),2)
        self.assertEqual(bisected_indices(times,900,900),1)
        self.assertEqual(bisected_indices(times,1500,900),1)
        self.assertEqual(bisected_indices(times,1200,3600),0)

if __name__=="__main__":unittest.main()