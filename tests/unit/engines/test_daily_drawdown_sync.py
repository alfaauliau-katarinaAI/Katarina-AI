"""One Owner daily drawdown threshold (35%) everywhere it is enforced or documented."""
import json
import unittest
from pathlib import Path

from katarina.engines.account_risk_state import DailyDrawdownTracker
from katarina.engines.risk import RiskGovernor
from katarina.intelligence.lab.evidence_risk import EvidenceRiskGate

ROOT = Path(__file__).resolve().parents[3]
OWNER_DAILY_STOP = .35


class DailyDrawdownSyncTests(unittest.TestCase):
    def test_config_is_the_owner_threshold(self):
        cfg = json.loads((ROOT / "config/risk_governor_v2.json").read_text())
        self.assertEqual(cfg["max_daily_drawdown_fraction"], OWNER_DAILY_STOP)
        self.assertEqual(cfg["drawdown_modes"]["emergency_at"], OWNER_DAILY_STOP)

    def test_every_enforcing_component_matches_config(self):
        governor = RiskGovernor.from_config(ROOT / "config/risk_governor_v2.json")
        self.assertEqual(governor.max_daily_drawdown, OWNER_DAILY_STOP)
        self.assertEqual(RiskGovernor().max_daily_drawdown, OWNER_DAILY_STOP)
        self.assertEqual(DailyDrawdownTracker().limit, OWNER_DAILY_STOP)
        self.assertEqual(EvidenceRiskGate.DAILY_STOP, OWNER_DAILY_STOP)

    def test_documented_profile_matches(self):
        manifest = (ROOT / "docs/stages/STAGE_01_40_MANIFEST.json").read_text()
        hardening = (ROOT / "docs/architecture/OPERATIONAL_HARDENING_V1.md").read_text()
        self.assertIn("35% daily drawdown", manifest)
        self.assertIn("35% daily drawdown", hardening)
        for text in (manifest, hardening):
            self.assertNotIn("10% daily drawdown", text)


if __name__ == "__main__":
    unittest.main()
