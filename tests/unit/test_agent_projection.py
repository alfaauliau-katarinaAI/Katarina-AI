"""Proof that the status UI never turns observation into a trading claim."""
import unittest

from katarina.monitoring.agent_projection import project_agent_board


class AgentProjectionTests(unittest.TestCase):
    def test_healthy_snapshot_is_not_live_or_profit_evidence(self):
        report = project_agent_board({
            "result": "PASS_READONLY_SNAPSHOT_ONLY",
            "assessed_at_utc": "2026-10-19T00:00:00+00:00",
            "received_market_data_symbols": 3, "cycles": 24,
            "successful_cycles": 24, "blockers": [],
        })
        self.assertEqual(report["architecture"], "SINGLE_UNIFIED_KATARINA_BRAIN")
        self.assertEqual(report["market_symbols"], 3)
        self.assertEqual(report["agent_workers_started"], 0)
        self.assertFalse(report["live_execution_authorized"])
        self.assertFalse(report["profit_verified"])
        self.assertEqual({a["id"] for a in report["lanes"]},
                         {"SCAN", "ANALYST", "STRATEGY", "BALANCE", "EXEC", "AUDIT"})
        self.assertEqual({a["id"]: a["status"] for a in report["lanes"]}["EXEC"], "LIVE_OFF")
        self.assertEqual({a["id"]: a["status"] for a in report["lanes"]}["ANALYST"], "NOT_ATTESTED")

    def test_stale_or_missing_snapshot_does_not_fabricate_activity(self):
        for payload in ({}, {"result": "BLOCKED",
                              "received_market_data_symbols": 11,
                              "cycles": 100,
                              "blockers": ["MARKET_TICK_MISSING_OR_STALE"]}, None):
            report = project_agent_board(payload)
            self.assertEqual(report["result"], "BLOCKED")
            self.assertIsNone(report["market_symbols"])
            self.assertEqual(report["lanes"][0]["status"], "BLOCKED")
            self.assertEqual(report["lanes"][-1]["status"], "BLOCKED")

    def test_unknown_delivery_is_not_claimed_disabled(self):
        report = project_agent_board({"result": "BLOCKED"}, delivery="UNKNOWN")
        self.assertEqual(report["delivery"], "UNVERIFIED")
        self.assertEqual(report["lanes"][4]["status"], "NOT_ATTESTED")
        self.assertFalse(report["live_execution_authorized"])

    def test_untrusted_blockers_are_bounded(self):
        report = project_agent_board({"blockers": ["STALE", "STALE", "x" * 500, 7]})
        self.assertEqual(report["blockers"], ["STALE"])


if __name__ == "__main__":
    unittest.main()
