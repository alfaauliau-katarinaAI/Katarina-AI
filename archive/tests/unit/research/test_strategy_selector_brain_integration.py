"""Archived with katarina.intelligence.brain (cleanup stage 2); not run by CI."""
import unittest
from katarina.intelligence.brain import KatarinaAIBrain
from tests.unit.research.test_strategy_selector import D, SelectorTests


class BrainIntegrationTests(unittest.TestCase):
    rows = SelectorTests.rows

    def test_brain_integration_is_research_only(self):
        selector,evidence=KatarinaAIBrain().train_strategy_selector(self.rows(),
            train_cutoff_ns=70*D,selection_end_ns=140*D)
        self.assertTrue(evidence["research_only"])
        self.assertFalse(evidence["live_risk_authorized"])

