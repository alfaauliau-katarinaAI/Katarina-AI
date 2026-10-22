"""Stage 3 synthetic proofs; never connects to a real broker."""
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from katarina.engines.demo_execution import DemoExecutionBoundary, DemoIntent
from katarina.engines.risk import RiskAction, RiskDecision, RiskGovernor, RiskRequest
from katarina.research.demo_readiness import DemoRiskLimits, DemoRiskOverlay, summarize_demo_outbox
from tests.unit.engines.test_demo_execution import Broker


class DemoRiskTests(unittest.TestCase):
    def setUp(self):
        self.governor = RiskGovernor()
        self.limits = DemoRiskLimits(.005, .03)  # Roadmap proposal, synthetic only.
        self.overlay = DemoRiskOverlay(self.governor, self.limits)
        self.request = RiskRequest(.01, 0, 0, .1, 2, True, True, risk_capital=1000)

    def test_caps_approved_risk_without_changing_main_governor(self):
        original = self.governor.evaluate(self.request)
        capped = self.overlay.evaluate(self.request)
        self.assertEqual(capped.action, RiskAction.REDUCE)
        self.assertEqual(capped.approved_fraction, .005)
        self.assertEqual(self.governor.evaluate(self.request), original)
        self.assertEqual(self.governor.max_daily_drawdown, .35)

    def test_daily_stop_at_boundary_and_all_upstream_vetoes_preserved(self):
        self.assertNotEqual(self.overlay.evaluate(replace(self.request, daily_drawdown_fraction=.029)).action,
                            RiskAction.PAUSE)
        self.assertEqual(self.overlay.evaluate(replace(self.request, daily_drawdown_fraction=.03)).reason,
                         "demo_daily_stop")
        for r in (replace(self.request, reconciled=False), replace(self.request, health_ok=False),
                  replace(self.request, unbounded_open_risk=True), replace(self.request, drawdown_fraction=.35),
                  replace(self.request, daily_drawdown_fraction=.35), replace(self.request, expected_rr=0)):
            decision = self.governor.evaluate(r)
            self.assertIn(decision.action, (RiskAction.REJECT, RiskAction.PAUSE))
            self.assertEqual(self.overlay.evaluate(r), decision)

    def test_grid_proves_overlay_never_increases_budget_or_relaxes_veto(self):
        for requested in (.0001, .003, .005, .01, .05):
            for open_risk in (0, .06, .079, .08):
                for daily in (0, .029, .03, .1, .35):
                    r = replace(self.request, requested_fraction=requested, open_risk_fraction=open_risk,
                                daily_drawdown_fraction=daily)
                    before, after = self.governor.evaluate(r), self.overlay.evaluate(r)
                    with self.subTest(requested=requested, open_risk=open_risk, daily=daily):
                        self.assertLessEqual(after.approved_fraction, before.approved_fraction)
                        self.assertLessEqual(after.approved_fraction, self.limits.per_trade_fraction)
                        if before.action in (RiskAction.PAUSE, RiskAction.REJECT):
                            self.assertEqual(after, before)

    def test_invalid_limits_and_upstream_fail_closed(self):
        for limits in ((float("nan"), .03), (.1, .03), (.005, .36), (True, .03), (0, .03)):
            with self.assertRaises(ValueError):
                DemoRiskLimits(*limits)
        class Invalid:
            def evaluate(self, request):
                return RiskDecision(RiskAction.APPROVE, float("nan"), "bad")
        self.assertEqual(DemoRiskOverlay(Invalid(), self.limits).evaluate(self.request).approved_fraction, 0)
        class Broken:
            def evaluate(self, request):
                raise RuntimeError("private")
        self.assertEqual(DemoRiskOverlay(Broken(), self.limits).evaluate(self.request).action, RiskAction.PAUSE)

    def test_existing_boundary_rejects_volume_above_reduced_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            broker = Broker()  # Fixed synthetic stop loss = 10 currency units.
            boundary = DemoExecutionBoundary(broker, self.overlay, Path(tmp) / "outbox.db", expected_login=123,
                                             expected_server="TEST-DEMO", stop_requested=lambda: False,
                                             clock=lambda: 1000.)
            intent = DemoIntent("test", "a" * 64, "TEST", "BUY", .01, 100, 90, 120, 1000.)
            result = boundary.submit(intent, self.request, risk_observed_at=1000., filling_mode=0)
            self.assertEqual(result["status"], "DEMO_VOLUME_EXCEEDS_APPROVED_RISK")
            self.assertEqual(broker.sent, [])
            # Cap allows exactly 10 only with verified capital 2000; no automatic lot increase.
            result = boundary.submit(intent, replace(self.request, risk_capital=2000),
                                     risk_observed_at=1000., filling_mode=0)
            self.assertEqual(result["status"], "DEMO_ACCEPTED")
            self.assertEqual(len(broker.sent), 1)


class DemoReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "outbox.db"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        # Create the actual schema using the existing boundary with a fake broker.
        DemoExecutionBoundary(Broker(), RiskGovernor(), self.path, expected_login=123,
                              expected_server="TEST-DEMO", stop_requested=lambda: False)

    def add(self, ident, state="CLOSED", profit=10, stamp=1000, side="BUY", position=None, **updates):
        outcome = dict(net_profit_native=profit, commission_native=-2, swap_native=-1, fee_native=-.5,
                       closed_observed_at=stamp, entry_slippage_price=.1, entry_volume=.01, deal_count=2,
                       prospective_broker_outcome=True, live_authorized=False)
        outcome.update(updates)
        self.db.execute("INSERT INTO demo_outbox(intent_id,digest,state,updated_at,intent_json,outcome_json,position_id) "
                        "VALUES(?,?,?,?,?,?,?)", (ident, "a" * 64, state, stamp,
                        json.dumps(dict(symbol="TEST", side=side)), json.dumps(outcome), position or int(ident)))
        self.db.commit()

    def report(self, **kwargs):
        return summarize_demo_outbox(self.db, currency="USD", **kwargs)

    def test_net_costs_drawdown_and_regime_side_summary(self):
        self.add("1", profit=20, stamp=1000)
        self.add("2", profit=-5, stamp=2000, side="SELL")
        self.add("3", profit=-10, stamp=3000)
        self.add("4", profit=5, stamp=4000)
        report = self.report(regimes={"1": "TREND", "2": "RANGE"},
                             decisions=[dict(decision_id="d1", action="WAIT", reasons=["SPREAD", "SPREAD"])])
        p = report["performance"]
        self.assertEqual(p["net_profit_native"], 10)  # Do not subtract broker costs twice.
        self.assertEqual(p["expectancy_native"], 2.5)
        self.assertAlmostEqual(p["profit_factor"], 25 / 15)
        self.assertEqual(p["realized_observation_order_drawdown_native"], 15)
        self.assertEqual(p["win_rate_net"], .5)
        self.assertEqual(p["commission_native"], -8)
        self.assertEqual(report["wait_reasons"], {"SPREAD": 1})
        self.assertEqual(report["coverage"]["closed_without_regime"], 2)
        self.assertEqual(report["reconciliation"]["rate"], 1)
        self.assertFalse(report["demo_execution_authorized"])

    def test_unknown_and_partial_block_reconciliation_without_entering_profit(self):
        for i, state in enumerate(("UNKNOWN", "PARTIAL", "ACCEPTED", "OWNERSHIP_REVIEW", "NEW_UNRECOGNIZED"), 1):
            self.add(str(i), state=state, profit=1000)
        self.add("6", state="REJECTED")
        self.add("7", state="OPEN")
        report = self.report()
        self.assertEqual(report["performance"]["closed_trades"], 0)
        self.assertEqual(report["reconciliation"]["unresolved_rows"], 5)
        self.assertEqual(report["rejected_orders"], 1)

    def test_missing_or_invalid_outcome_does_not_become_zero_profit(self):
        self.add("1", net_profit_native=None)
        self.add("2", prospective_broker_outcome=False)
        self.add("3", deal_count=0)
        self.add("4", entry_slippage_price=None)
        report = self.report()
        self.assertEqual(report["performance"]["closed_trades"], 1)
        self.assertEqual(report["reconciliation"]["unresolved_rows"], 3)
        self.assertEqual(report["coverage"]["closed_without_slippage"], 1)
        self.assertEqual(report["entry_slippage_by_symbol"], {})

    def test_duplicate_position_cannot_double_count_profit(self):
        self.add("1", position=5)
        self.add("2", position=5)
        report = self.report()
        self.assertEqual(report["performance"]["closed_trades"], 0)
        self.assertEqual(report["reconciliation"]["problems"], {"INVALID_OR_DUPLICATE_POSITION": 2})

    def test_empty_and_no_loss_reports_are_honest(self):
        self.assertEqual(self.report()["reconciliation"]["status"], "NO_DATA")
        self.add("1")
        p = self.report()["performance"]
        self.assertIsNone(p["profit_factor"])
        self.assertEqual(p["profit_factor_state"], "NO_LOSSES")

    def test_report_deterministic_and_read_only(self):
        self.add("2", stamp=2000)
        self.add("1", stamp=1000)
        before = self.path.read_bytes()
        self.db.execute("PRAGMA query_only=ON")
        a = self.report()
        b = self.report()
        self.assertEqual(a, b)
        self.assertEqual(before, self.path.read_bytes())
        self.assertNotIn("intent_id", json.dumps(a))

    def test_invalid_decisions_and_unknown_regime_ids_rejected(self):
        for decisions in ([dict(decision_id="d", action="WAIT", reasons=[])],
                          [dict(decision_id="d", action="BUY")] * 2):
            with self.assertRaises(ValueError):
                self.report(decisions=decisions)
        with self.assertRaises(ValueError):
            self.report(regimes={"absent": "TREND"})

    def test_cli_read_only_and_input_overwrite_guard(self):
        self.add("1")
        self.db.close()
        output = Path(self.tmp.name) / "report.json"
        script = Path(__file__).resolve().parents[3] / "scripts/research/check_demo_readiness.py"
        command = [sys.executable, str(script), "--outbox", str(self.path), "--currency", "USD", "--output"]
        before = self.path.read_bytes()
        result = subprocess.run(command + [str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, self.path.read_bytes())
        self.assertFalse(json.loads(output.read_text())["live_execution_authorized"])
        denied = subprocess.run(command + [str(self.path)], capture_output=True, text=True)
        self.assertNotEqual(denied.returncode, 0)
        self.assertEqual(before, self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
