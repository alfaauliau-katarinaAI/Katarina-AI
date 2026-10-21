"""Regression checks for honest Master Design traceability and release gates."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from scripts.ai.verify_master_design_traceability import (
    ROOT, audit_master_design,
)

MANIFEST = ROOT / "config" / "master_design_traceability_v1.json"


class MasterDesignTraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text())

    def test_authoritative_approved_areas_and_six_deferred_topics_accounted(self):
        output = audit_master_design(root=ROOT, manifest=self.manifest)
        self.assertEqual(output["registered_approved_areas"], 18)
        self.assertEqual(output["deferred_owner_decisions"], 6)
        self.assertEqual(output["counts"], {
            "OFFLINE_VERIFIED": 4, "PARTIAL": 11,
            "NOT_INTEGRATED": 2, "REMOVED": 1,
        })
        self.assertEqual(output["readiness"], "OFFLINE_ENGINEERING_ONLY")
        self.assertFalse(output["master_design_fully_implemented"])
        self.assertFalse(output["deferred_decisions_resolved"])
        self.assertFalse(output["live_trading_authorized"])
        self.assertEqual(output["areas"]["A18"], "REMOVED")
        self.assertGreater(output["files_with_verified_sha256"], 20)

    def test_missing_approved_rule_or_deferred_decision_refused(self):
        for field in ("approved_areas", "deferred_decisions"):
            changed = deepcopy(self.manifest)
            changed[field].pop()
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                        ValueError, "master_design_area_or_decision_missing"):
                    audit_master_design(manifest=changed, run_acceptance=False)

    def test_unsafe_status_promotion_or_management_activation_refused(self):
        for id_, status in (("A03", "OFFLINE_VERIFIED"),
                            ("A13", "OFFLINE_VERIFIED"),
                            ("A18", "PARTIAL")):
            changed = deepcopy(self.manifest)
            next(a for a in changed["approved_areas"] if a["id"] == id_)["status"] = status
            with self.subTest(id=id_, status=status):
                with self.assertRaisesRegex(
                        ValueError, "mismatch|unsubstantiated"):
                    audit_master_design(manifest=changed, run_acceptance=False)

    def test_missing_or_external_evidence_paths_refused(self):
        for value in ("../../credentials.txt", "src/does_not_exist.py"):
            changed = deepcopy(self.manifest)
            changed["approved_areas"][0]["evidence_paths"] = [value]
            with self.subTest(path=value):
                with self.assertRaisesRegex(
                        ValueError, "path|missing_or_outside"):
                    audit_master_design(manifest=changed, run_acceptance=False)

    def test_deferred_decisions_are_not_silently_resolved(self):
        changed = deepcopy(self.manifest)
        changed["deferred_decisions"][0]["status"] = "DECIDED"
        with self.assertRaisesRegex(ValueError, "deferred_owner_decision_invented"):
            audit_master_design(manifest=changed, run_acceptance=False)

    def test_canonical_acceptance_cannot_claim_live_or_bypass_lockdown(self):
        from scripts.ai import verify_master_design_traceability as audit
        bad = {
            "status":"INTEGRATED_OFFLINE_ENGINEERING_ONLY",
            "modules_verified":17,
            "orders_submitted":0,
            "live_execution_authorized":True,
            "management":"REMOVED",
            "cumulative_profit_lock":"VERIFIED_THREE_MILESTONES_AND_RESTART",
            "same_day_emergency_lockdown":"VERIFIED_NO_NEW_ENTRY",
        }
        with patch.object(audit, "verify", return_value=bad):
            with self.assertRaisesRegex(
                    ValueError, "master_design_canonical_acceptance_failed"):
                audit_master_design(manifest=self.manifest)
        bad["live_execution_authorized"] = False
        bad["same_day_emergency_lockdown"] = "BYPASS"
        with patch.object(audit, "verify", return_value=bad):
            with self.assertRaisesRegex(
                    ValueError, "master_design_canonical_acceptance_failed"):
                audit_master_design(manifest=self.manifest)


if __name__ == "__main__":
    unittest.main()
