"""Paired direction baseline never confuses a negative control with live PnL."""
import unittest
import tempfile,json
from pathlib import Path
from katarina.intelligence.perception.symbol_playbooks import SYMBOLS
import sys
SCRIPTS=Path(__file__).resolve().parents[3]/"scripts"/"research"
sys.path.insert(0,str(SCRIPTS))
from compare_playbook_to_opposite_entry import paired_mean_block_ci,results,extract

class MirrorTests(unittest.TestCase):
    def _row(self,day,delta):
        return dict(symbol="NAS100.vx",family=SYMBOLS["NAS100.vx"],
                    signal_close_utc=day+"T14:00:00+00:00",
                    delta_original_minus_mirror_R=delta,
                    original_R=.4,mirror_R=.4-delta)

    def test_deterministic_day_block_bootstrap(self):
        a=[self._row("2026-07-02",.6),
           self._row("2026-07-02",.8),
           self._row("2026-07-03",-.1)]
        ci=paired_mean_block_ci(a)
        self.assertEqual(ci,paired_mean_block_ci(a))
        self.assertLess(ci[0],ci[1])

    def test_mirror_cohort_difference_exact(self):
        a=[self._row("2026-07-02",.6),self._row("2026-07-03",.4)]
        report=results(a)[0]
        self.assertAlmostEqual(report["average_R_lift"],.5)
        self.assertFalse(report["enough_independent_evidence"])

    def test_input_permissions_checked(self):
        doc=dict(kind="distinct_per_symbol_research_playbooks_v1",
                 live_execution_enabled=True,model_promotion_allowed=False,
                 trials=[])
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"bad.json"
            file.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,"untrusted_or_trading_enabled_archive"):
                extract([file])

if __name__=="__main__":
    unittest.main()
