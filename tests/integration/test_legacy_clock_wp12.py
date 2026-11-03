"""WP12: legacy MT5 acquisition refuses unverified bar history; no orders.

The standalone legacy decision observer (run_readonly_decisions.py) was removed in
cleanup B1 (3 Nov 2026); only the canonical observer acquires broker data.
"""
import unittest
from unittest.mock import Mock

from katarina.intelligence.perception import screening


class LegacyClockTests(unittest.TestCase):
    def test_screening_refuses_unverified_history_before_any_broker_access(self):
        broker = Mock()
        broker.initialize.return_value = False
        with self.assertRaisesRegex(RuntimeError, '^BROKER_BAR_CLOCK_NOT_VERIFIED_WP12$'):
            screening.collect(broker, 'unused-research-terminal')
        self.assertEqual(broker.mock_calls, [])

    def test_removed_legacy_observer_scripts_stay_removed(self):
        from pathlib import Path
        scripts = Path(__file__).resolve().parents[2] / 'scripts' / 'ai'
        for name in ('run_readonly_decisions.py', 'RUN_READONLY_DECISIONS.cmd',
                     'smoke_closed_market_decision.py'):
            self.assertFalse((scripts / name).exists(), name)


if __name__ == '__main__':
    unittest.main()
