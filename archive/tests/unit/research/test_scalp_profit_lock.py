import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"scripts/research"))
from run_scalp_exit_experiments import audit_lock_rows,freeze

class ProfitLockAuditTests(unittest.TestCase):
    def row(self):
        return dict(side="1",entry="100",initial_risk="2",bid="101.5",ask="101.7",
                    old_sl="98",new_sl="100.1",trigger_r=".75",lock_r=".05")
    def test_buy(self):
        self.assertEqual(audit_lock_rows([self.row()])["modifications"],1)
    def test_sell(self):
        r=self.row();r.update(side="-1",bid="98.3",ask="98.5",old_sl="102",new_sl="99.9")
        self.assertTrue(audit_lock_rows([r])["monotonic_stop_verified"])
    def test_premature_trigger_rejected(self):
        r=self.row();r["bid"]="101.4"
        with self.assertRaises(ValueError):audit_lock_rows([r])
    def test_stop_widening_rejected(self):
        r=self.row();r["old_sl"]="100.2"
        with self.assertRaises(ValueError):audit_lock_rows([r])
    def test_wrong_lock_amount_rejected(self):
        r=self.row();r["new_sl"]="100.3"
        with self.assertRaises(ValueError):audit_lock_rows([r])
    def test_nonfinite_rejected(self):
        r=self.row();r["new_sl"]="nan"
        with self.assertRaises(ValueError):audit_lock_rows([r])
    def test_empty_is_valid_unexercised(self):
        self.assertEqual(audit_lock_rows([])["modifications"],0)
    def test_session_eligibility_is_constant(self):
        m=freeze()
        self.assertEqual(len(m["candidates"]),8)
        for c in m["candidates"]:
            s=c["settings"]
            self.assertEqual(s["InpZoneMaxHoldMinutes"]+s["InpZoneSessionBufferMinutes"],105)

if __name__=="__main__":unittest.main()
