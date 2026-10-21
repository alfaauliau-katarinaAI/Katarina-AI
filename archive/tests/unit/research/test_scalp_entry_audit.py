import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"scripts/research"))
from run_scalp_entry_comparison import audit_fills,freeze

class ScalpEntryAuditTests(unittest.TestCase):
    def row(self):
        return dict(side="1",entry_time="400",signal_time="340",context_known="300",
            method="8",context_tf="PERIOD_M5",initial_risk_cash="9.9",risk_budget="10",
            entry="100",sl="97.4",atr="2",context_adx="25",context_regime="UP",
            seconds_to_session_close="7200")
    def test_valid_trend(self):
        self.assertTrue(audit_fills([self.row()],1,8)["regime_verified"])
    def test_range_is_allowed_without_direction_gate(self):
        r=self.row();r.update(method="9",context_adx="15",context_regime="DOWN")
        self.assertTrue(audit_fills([r],1,9)["regime_verified"])
    def test_future_context_rejected(self):
        r=self.row();r["context_known"]="401"
        with self.assertRaises(ValueError):audit_fills([r],1,8)
    def test_wrong_direction_rejected(self):
        r=self.row();r["context_regime"]="DOWN"
        with self.assertRaises(ValueError):audit_fills([r],1,8)
    def test_range_high_adx_rejected(self):
        r=self.row();r.update(method="9",context_adx="30")
        with self.assertRaises(ValueError):audit_fills([r],1,9)
    def test_risk_and_stop_rejected(self):
        for key,value in (("initial_risk_cash","11"),("sl","101"),("atr","nan")):
            r=self.row();r[key]=value
            with self.assertRaises(ValueError):audit_fills([r],1,8)
    def test_session_or_missing_fill_rejected(self):
        r=self.row();r["seconds_to_session_close"]="600"
        with self.assertRaises(ValueError):audit_fills([r],1,8)
        with self.assertRaises(ValueError):audit_fills([],1,8)
    def test_four_equal_risk_candidates(self):
        m=freeze();self.assertEqual(len(m["candidates"]),4)
        for c in m["candidates"]:
            self.assertEqual(c["rr"],1.5)
            self.assertEqual(c["settings"]["InpZoneRiskCash"],10)

if __name__=="__main__":unittest.main()
