"""Tamper-resistant audit for the archived TP/SL tick-path results."""
import sys
import tempfile
import unittest
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone

SCRIPT_DIR=Path(__file__).resolve().parents[3]/"scripts"/"research"
sys.path.insert(0,str(SCRIPT_DIR))
from replay_historical_tick_stops import (
    CONFIG,FEE_STRESS_BPS,COST_CEILINGS,simulate,summarize
)
from audit_tick_sl_tp_paths import inspect

def report():
    opening=datetime.fromtimestamp(1000,timezone.utc).isoformat()
    ticks=[(1000.,100.,100.1),(1001.,101.1,101.3)]
    ticks.extend((float(t),101.1,101.3) for t in range(1060,2801,60))
    records=[]
    for tp,sl in CONFIG:
        for extra in FEE_STRESS_BPS:
            x=simulate(ticks,"BUY",1.,tp,sl,extra)
            x.update(dict(symbol="DEMO",side="BUY",family="M1_M5",
                tick_path_sha256="a"*64,tick_events_available=len(ticks),
                month="1970-01",tp_atr=tp,sl_atr=sl,
                extra_cost_bps=extra,signal_bar_close_utc=opening,
                entry_time_utc=opening,entry_spread_atr=.1,
                atr_verified_from_sha256=True,trade_filled=False,
                model_promotion_allowed=False))
            records.append(x)
    rows=[]
    for family in ("M1_M5","M5_M15"):
        for cost in COST_CEILINGS:
            for tp,sl in CONFIG:
                for extra in FEE_STRESS_BPS:
                    for side in ("BUY","SELL"):
                        arr=[x for x in records if x["family"]==family and
                             x["side"]==side and x["entry_spread_atr"]<=cost
                             and x["tp_atr"]==tp and x["sl_atr"]==sl
                             and x["extra_cost_bps"]==extra]
                        rows.append(dict(family=family,spread_atr_limit=cost,
                             tp_atr=tp,sl_atr=sl,side=side,extra_bps=extra,
                             **summarize(arr)))
    return dict(report_version="historical_ohlc_verified_bidask_tick_path_v1",
       live_execution_enabled=False,model_promotion_allowed=False,
       strategy_approved=False,true_broker_commissions_unknown=True,
       scenario_records=records,total_scenario_rows=len(records),
       groups=rows,input_evidence={"M1_M5":[],"M5_M15":[]})

class IntegrityTests(unittest.TestCase):
    def test_valid_scenario_archive(self):
        result=inspect(report())
        self.assertEqual(result["scenario_rows"],12)
        self.assertEqual(result["unique_quote_entry_candidates"],1)
        self.assertFalse(result["strategy_approved"])

    def test_forged_positive_r_is_rejected(self):
        d=report()
        d["scenario_records"][0]["stressed_r"]+=.5
        with self.assertRaisesRegex(ValueError,"replay_math_mismatch"):
            inspect(d)

    def test_forged_exit_label_is_rejected(self):
        d=report()
        d["scenario_records"][0]["exit_reason"]="TIME"
        with self.assertRaisesRegex(ValueError,"bad_time_exit"):
            inspect(d)

    def test_changed_aggregate_is_rejected(self):
        d=report()
        group=next(x for x in d["groups"] if x["n_closed"]==1)
        group["profit_factor"]=1234
        with self.assertRaisesRegex(ValueError,"summary_math_mismatch"):
            inspect(d)

    def test_source_sha_changed_is_rejected(self):
        d=report()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"source.json"
            p.write_text("original")
            d["input_evidence"]["M1_M5"]=[dict(input_path=str(p),
                  sha256=sha256(b"original").hexdigest())]
            self.assertEqual(inspect(d)["source_files_verified"],1)
            p.write_text("changed")
            with self.assertRaisesRegex(ValueError,"altered_input_archive"):
                inspect(d)

    def test_live_flag_is_rejected(self):
        d=report()
        d["live_execution_enabled"]=True
        with self.assertRaisesRegex(ValueError,"risk_permission_changed"):
            inspect(d)

if __name__=="__main__":
    unittest.main()
