"""CI enforcement of the roadmap promotion gate (docs/ROADMAP.md, 'Gerbang promosi')."""
import unittest
from pathlib import Path

from katarina.governance.promotion_gate import LOCK_PATH, check, load_json

ROOT = Path(__file__).resolve().parents[2]


class PromotionGateTests(unittest.TestCase):
    def test_active_decision_and_risk_files_match_an_approved_promotion(self):
        violations = check(ROOT)
        self.assertEqual(
            violations, [],
            "Berkas keputusan/risiko aktif berubah tanpa catatan promosi yang sah. Ikuti docs/ROADMAP.md "
            "'Gerbang promosi': laporan validasi PASS + persetujuan Owner, lalu "
            "`python scripts/governance/promotion_gate.py --write-lock <record>`.\n" + "\n".join(violations))

    def test_lock_covers_the_risk_governor_and_decision_brain(self):
        files = load_json(ROOT / LOCK_PATH)["files"]
        for required in ("src/katarina/engines/risk.py", "config/risk_governor_v2.json",
                         "src/katarina/intelligence/cognition/market_decision.py",
                         "src/katarina/intelligence/cognition/market_decision_pipeline.py",
                         "src/katarina/engines/demo_execution.py"):
            self.assertIn(required, files)


if __name__ == "__main__":
    unittest.main()
