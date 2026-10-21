"""Historical market sample memory: prospective-only, no cross pair or leaks."""
import sys,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
SCRIPTS=Path(__file__).resolve().parents[3]/"scripts"/"research"
sys.path.insert(0,str(SCRIPTS))
from katarina.intelligence.perception.historical_analog_memory import (
    fit_history,query_analogs,load_frozen_symbol_memory)
from probe_current_market_analogs import evaluate_observer

UTC=timezone.utc
DAY=datetime(2026,8,17,0,0,tzinfo=UTC)

def make_record(n,symbol="NAS100.vx",predict=False):
    d=DAY+timedelta(hours=6*n) if not predict else datetime(2026,10,12,16,tzinfo=UTC)
    bull=n%3!=0
    frm={tf:dict(direction="UP" if bull else "DOWN",
                adx14=22.+(n%8),plus_di14=25.+n%10,
                minus_di14=19.+n%9,efficiency=.25+.01*(n%12))
         for tf in ("M5","M15","H1")}
    src=dict(symbol=symbol,regime="CONTINUATION_UP" if bull else "CONTINUATION_DOWN",
             frames=frm,close_time_utc=d.isoformat())
    return dict(source=src,symbol=symbol,period="august",regime=src["regime"],
        signal_time=d.timestamp(),label_end=(d+timedelta(hours=1)).timestamp(),y=int(bull))

class HistoricalAnalogUnitTests(unittest.TestCase):
    def setUp(self):
        self.rows=[make_record(i) for i in range(40)]
        self.memory=fit_history(self.rows,"NAS100.vx",1)
        self.new=make_record(45,predict=True)

    def test_past_neighbors_report_provenance(self):
        result=query_analogs(self.memory,self.new["source"],self.new["signal_time"])
        self.assertIn(result["status"],("CANDIDATE","ABSTAIN_WEAK_ANALOG_SIGNAL"))
        self.assertEqual(result["symbol"],"NAS100.vx")
        self.assertEqual(len(result["neighbors"]),3)
        self.assertTrue(all(x["label_resolved_before_prediction"] for x in result["neighbors"]))
        self.assertTrue(all(x["similarity_distance"]>=0 for x in result["neighbors"]))
        self.assertFalse(result["confidence_calibrated"])
        self.assertFalse(result["is_executable_trading_probability"])

    def test_never_match_another_broker_symbol(self):
        with self.assertRaisesRegex(ValueError,"cross_symbol_or_empty_analog_memory"):
            fit_history(self.rows[:-1]+[make_record(41,"XAUUSD.vx")],"NAS100.vx",1)
        foreign=make_record(45,"XAUUSD.vx",predict=True)
        with self.assertRaisesRegex(ValueError,"cross_symbol_prediction_forbidden"):
            query_analogs(self.memory,foreign["source"],foreign["signal_time"])

    def test_future_result_cannot_be_used_as_neighbor(self):
        m=dict(self.memory)
        import numpy as np
        m["label_end"]=np.array([self.new["signal_time"]+3600.]*len(self.rows))
        r=query_analogs(m,self.new["source"],self.new["signal_time"])
        self.assertEqual(r["status"],"ABSTAIN_NO_RESOLVED_ANALOGS")
        self.assertIsNone(r["p_up"])

    def test_future_clock_or_stale_request_rejected(self):
        with self.assertRaisesRegex(ValueError,"stale_or_future_prediction_snapshot"):
            query_analogs(self.memory,self.new["source"],self.new["signal_time"]-1)
        with self.assertRaisesRegex(ValueError,"stale_or_future_prediction_snapshot"):
            query_analogs(self.memory,self.new["source"],self.new["signal_time"]+3600)

    def test_unknown_regime_abstains(self):
        source=dict(self.new["source"],regime="UNKNOWN")
        x=query_analogs(self.memory,source,self.new["signal_time"])
        self.assertEqual(x["status"],"ABSTAIN_UNKNOWN")
        self.assertIsNone(x["p_up"])

    def test_duplicate_future_only_memory_is_forbidden(self):
        frozen=dict(kind="frozen_per_symbol_historical_analog_memory_v1",
            no_live_orders=True,model_promotion_allowed=False,
            sample_feature_version="causal_mtf_14plus_regime7_v1",
            asof_utc="2026-10-10T12:00:00+00:00",by_symbol={})
        with self.assertRaisesRegex(ValueError,"frozen_memory_cannot_predict_past_training_period"):
            load_frozen_symbol_memory(frozen,"NAS100.vx",1,
                      datetime(2026,10,1,tzinfo=UTC).timestamp())

    def test_live_observer_closed_market_abstains_without_orders(self):
        frozen=dict(by_symbol={"NAS100.vx":{}})
        latest=dict(as_of_utc=self.new["source"]["close_time_utc"],
            symbols=[dict(symbol="NAS100.vx",
                          market_regime_v1=dict(regime="UNKNOWN",
                            entry_authorized=False,observed_utc=None,frames={}))])
        result=evaluate_observer(frozen,latest,
            datetime(2026,10,12,16,tzinfo=UTC))
        self.assertEqual(result["by_symbol"][0]["status"],
                         "ABSTAIN_INVALID_OR_MISSING_REGIME")
        self.assertEqual(result["decision"],"NO_TRADE")
        self.assertFalse(result["live_execution_enabled"])

if __name__=="__main__":
    unittest.main()
