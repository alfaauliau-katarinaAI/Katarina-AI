from __future__ import annotations

import importlib
import unittest

from katarina.body import STAGE_MODULES
from katarina.body.functional import LivePreflightCheck


def component(stage: int):
    return importlib.import_module(STAGE_MODULES[stage]).Component()


class Stage36LivePreflightGuardTests(unittest.TestCase):
    def test_complete_live_preflight_passes_without_broker_mutation(self):
        c = component(36)
        self.assertFalse(c.broker_mutation_enabled)
        checks = tuple(
            LivePreflightCheck(name, True)
            for name in c.REQUIRED_CHECKS
        )
        out = c.evaluate(checks)
        self.assertTrue(out["passed"])
        self.assertEqual(out["missing_checks"], ())
        self.assertFalse(out["broker_mutation"])
        self.assertFalse(out["live_execution_authority"])

    def test_missing_live_preflight_check_fails_closed(self):
        c = component(36)
        checks = tuple(
            LivePreflightCheck(name, name != "health_ready")
            for name in c.REQUIRED_CHECKS
        )
        out = c.evaluate(checks)
        self.assertFalse(out["passed"])
        self.assertIn("health_ready", out["missing_checks"])

    def test_duplicate_live_preflight_check_is_rejected(self):
        c = component(36)
        with self.assertRaises(ValueError):
            c.evaluate((
                LivePreflightCheck("terminal_connected", True),
                LivePreflightCheck("terminal_connected", True),
            ))


class Stage38MicroRiskGateTests(unittest.TestCase):
    def test_missing_prerequisites_are_explicit(self):
        out = component(38).validate({})
        self.assertFalse(out["approved"])
        self.assertFalse(out["all_prerequisites_present"])
        self.assertEqual(
            set(out["missing_prerequisites"]),
            {
                "strategy_policy_finalized",
                "risk_policy_finalized",
                "stage35_tester_passed",
                "stage36_live_preflight_passed",
                "stage37_stress_passed",
                "health_ready",
                "reconciliation_ready",
            },
        )

    def test_even_complete_prerequisites_do_not_enable_live_in_body_build(self):
        payload = {
            "strategy_policy_finalized": True,
            "risk_policy_finalized": True,
            "stage35_tester_passed": True,
            "stage36_live_preflight_passed": True,
            "stage37_stress_passed": True,
            "health_ready": True,
            "reconciliation_ready": True,
        }
        out = component(38).validate(payload)
        self.assertTrue(out["all_prerequisites_present"])
        self.assertEqual(out["missing_prerequisites"], ())
        self.assertFalse(out["approved"])
        self.assertFalse(out["live_risk_ready"])
        self.assertFalse(out["live_execution_authority"])


if __name__ == "__main__":
    unittest.main()
