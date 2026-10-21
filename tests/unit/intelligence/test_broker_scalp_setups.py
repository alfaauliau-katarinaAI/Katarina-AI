"""Focused causal signal & broker execution perturbation tests."""
import sys,unittest
from datetime import datetime,timezone
from pathlib import Path

SCRIPTS=Path(__file__).resolve().parents[3]/"scripts"/"research"
sys.path.insert(0,str(SCRIPTS))
from benchmark_broker_scalp_setups import (
    ema_series,slip_ticks_and_replay,make_summary)
from katarina.intelligence.scalp_pattern_candidates import propose_family

UTC=timezone.utc
NOW=datetime(2026,10,8,12,tzinfo=UTC)

def samples(period,n,end_time):
    close=int(NOW.timestamp())
    rows=[]
    for i in range(n):
        p=100+i*.1
        rows.append(dict(time=float(close-period*(n-i)),open=p,
                         high=p+.10,low=p-.10,close=p+.05,
                         tick_volume=100))
    return rows

class BrokerSetupsTests(unittest.TestCase):
    def test_no_signal_with_fewer_than_120_closed_bars(self):
        m1=samples(60,119,0)
        m5=samples(300,120,0)
        self.assertEqual(propose_family(m1,m5,NOW),[])

    def test_ema_series_never_uses_future_bars(self):
        x=samples(60,120,0)
        ema=ema_series(x)
        for i in (0,20,50,119):
            self.assertAlmostEqual(ema[i],ema_series(x[:i+1])[-1])

    def test_perturbation_always_reduces_outcome_on_short_path(self):
        ticks=[(1000.,100.,100.1),(1001.,101.,101.1)]
        a=slip_ticks_and_replay(ticks,"BUY",1.,.5,1.,0,.01)
        b=slip_ticks_and_replay(ticks,"BUY",1.,.5,1.,1,.01)
        c=slip_ticks_and_replay(ticks,"BUY",1.,.5,1.,3,.01)
        self.assertEqual(a["status"],"CLOSED")
        self.assertGreater(a["stressed_r"],b["stressed_r"])
        self.assertGreater(b["stressed_r"],c["stressed_r"])

    def test_short_slippage_increases_total_loss(self):
        ticks=[(1000.,100.,100.1),(1001.,101.3,101.4)]
        a=slip_ticks_and_replay(ticks,"SELL",1.,2.,1.,0,.01)
        b=slip_ticks_and_replay(ticks,"SELL",1.,2.,1.,2,.01)
        self.assertEqual(a["exit_reason"],"SL")
        self.assertLess(b["stressed_r"],a["stressed_r"])

    def test_summary_measures_missing_and_risk_drawdown(self):
        rows=[dict(status="CLOSED",R=1.,usd_minlot=1.,
                   exit_reason="TP",signal_close_utc="2026-08-19T10:00:00+00:00"),
              dict(status="CLOSED",R=-1.,usd_minlot=-1.,
                   exit_reason="SL",signal_close_utc="2026-08-20T10:00:00+00:00"),
              dict(status="TIME_QUOTE_MISSING")]
        out=make_summary(rows)
        self.assertEqual(out["closed"],2)
        self.assertAlmostEqual(out["mean_r"],0.)
        self.assertAlmostEqual(out["largest_peak_to_trough_r"],1.)
        self.assertEqual(out["missing"]["TIME_QUOTE_MISSING"],1)
        self.assertFalse(out["enough_evidence"])

if __name__=="__main__":
    unittest.main()
