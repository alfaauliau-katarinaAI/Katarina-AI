import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"scripts/research"))
from run_zone_scalp_experiments import audit_zone_rows,freeze

class ZoneAuditTests(unittest.TestCase):
    def row(self):
        return dict(side="1",base_time="100",zone_known="200",first_touch="260",
            signal_time="320",entry_time="380",confirmation_known="350",confirmation_used="true",
            cash_risk="9.5",risk_budget="10",entry="105",sl="98",zone_low="99",zone_high="100")
    def test_valid_fill(self):
        self.assertTrue(audit_zone_rows([self.row()],1)["risk_budget_verified"])
    def test_future_confirmation_rejected(self):
        r=self.row();r["confirmation_known"]="400"
        with self.assertRaises(ValueError): audit_zone_rows([r],1)
    def test_touch_before_zone_exists_rejected(self):
        r=self.row();r["first_touch"]="150"
        with self.assertRaises(ValueError): audit_zone_rows([r],1)
    def test_risk_escalation_rejected(self):
        r=self.row();r["cash_risk"]="10.1"
        with self.assertRaises(ValueError): audit_zone_rows([r],1)
    def test_repeated_zone_rejected(self):
        with self.assertRaises(ValueError): audit_zone_rows([self.row(),self.row()],2)
    def test_missing_fill_rejected(self):
        with self.assertRaises(ValueError): audit_zone_rows([],1)
    def test_stop_inside_zone_rejected(self):
        r=self.row();r["sl"]="99.5"
        with self.assertRaises(ValueError): audit_zone_rows([r],1)
    def test_predeclared_unique_matrix(self):
        m=freeze()
        self.assertEqual(len(m["candidates"]),12)
        self.assertEqual(len({c["id"] for c in m["candidates"]}),12)
        self.assertTrue(m["october_reserved"])

if __name__=="__main__": unittest.main()
