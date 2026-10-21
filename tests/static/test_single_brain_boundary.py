"""Keep the approved logical boundary enforceable when launchers change."""
import ast
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SingleBrainBoundaryTests(unittest.TestCase):
    def test_launcher_has_no_independent_observation_or_broker_implementation(self):
        source = (ROOT/'scripts/ai/run_contextual_market_observer.py').read_text()
        tree = ast.parse(source)
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertIn('katarina.intelligence.cognition.unified_brain', imports)
        for forbidden in ('MetaTrader5', 'MemoryStore(', 'ContextStore(', 'MarketDecisionBrain(',
                          'virtual_book.', 'order_send(', 'threading', 'subprocess'):
            self.assertNotIn(forbidden, source)

    def test_internal_gate_cannot_construct_risk_authority_or_send_to_broker(self):
        root = ROOT/'src/katarina/intelligence/cognition'
        for name in ('unified_brain.py', 'observer.py', 'brain_runtime_control.py'):
            tree = ast.parse((root/name).read_text())
            for call in (x for x in ast.walk(tree) if isinstance(x, ast.Call)):
                if isinstance(call.func, ast.Name):
                    self.assertNotEqual(call.func.id, 'RiskGovernor', name)
                if isinstance(call.func, ast.Attribute):
                    self.assertNotIn(call.func.attr, ('order_send', 'order_check', 'Popen'), name)

    def test_cold_import_requires_no_terminal_and_starts_no_external_worker(self):
        source = ('import sys; import katarina.intelligence.cognition.unified_brain; '
                  'import katarina.intelligence.cognition.observer; '
                  'assert "MetaTrader5" not in sys.modules')
        result = subprocess.run([sys.executable, '-c', source], cwd=ROOT,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_observers_cannot_start_an_independent_brain_or_loop(self):
        for name in ('run_market_brain.py', 'run_decision_brain_v3.py'):
            with self.subTest(name=name):
                result = subprocess.run([sys.executable, str(ROOT/'scripts/ai'/name)],
                    cwd=ROOT, capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('LEGACY_OBSERVER_DISABLED', result.stderr)
                source = (ROOT/'scripts/ai'/name).read_text()
                self.assertNotIn('import MetaTrader5', source)
                self.assertNotIn('while ', source)
