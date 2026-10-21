"""Read-only adaptive Entry/Exit handoff acceptance tests."""
from dataclasses import replace
from datetime import datetime, timezone
import unittest

from katarina.engines.adaptive_scalper import ResearchEntryPlan, ScalpSide
from katarina.intelligence.perception.adaptive_regime import MarketRead, MarketState, Playbook
from katarina.intelligence.cognition.adaptive_observation import BrainV2Observation
from katarina.intelligence.perception.structure_exit_plan import StructuralExitPlan
from katarina.intelligence.cognition.unified_research_handoff import research_handoff

CLOCK = datetime(2026, 10, 14, 13, 30, tzinfo=timezone.utc)
HASH = "a" * 64


def brain(side=ScalpSide.BUY, ready=True):
    regime = MarketRead(MarketState.TREND_UP, Playbook.TREND_PULLBACK,
                        1, .7, "NORMAL", ("closed_bar",))
    proposal = ResearchEntryPlan("XAUUSD", regime.state, regime.playbook,
                                 side, ready, ("closed_bar",), 0.)
    return BrainV2Observation(regime, proposal, None)


def exit_plan(side="BUY", stop=1990., target=2030., ready=True):
    return StructuralExitPlan(side, ready, stop, target, 10., 3.,
                              "closed_swing", "target",
                              () if ready else ("not_ready",))


def handoff(**changes):
    args = dict(brain=brain(), exit_plan=exit_plan(), symbol="XAUUSD",
                entry=2000., as_of_utc=CLOCK, source_digest=HASH,
                hand_id="hand-shadow-01")
    args.update(changes)
    return research_handoff(**args)


class UnifiedResearchHandoffTests(unittest.TestCase):
    def test_matching_buy_entry_and_exit_research_only(self):
        r = handoff()
        self.assertEqual(r.action, "RESEARCH_CANDIDATE")
        self.assertEqual((r.stop, r.target), (1990., 2030.))
        self.assertTrue(r.research_only)
        self.assertFalse(r.live_execution_authorized)
        self.assertFalse(r.strategy_promoted)
        self.assertEqual(r.orders_submitted, 0)
        self.assertEqual(r.owner_view()["controls"], "READ_ONLY")
        self.assertEqual(r.owner_view()["hand_trust"], "UNVERIFIED_TELEMETRY")

    def test_sell_has_independent_exit_geometry(self):
        r = handoff(brain=brain(ScalpSide.SELL),
                    exit_plan=exit_plan("SELL", 2010., 1970.))
        self.assertEqual((r.side, r.action), ("SELL", "RESEARCH_CANDIDATE"))
        self.assertFalse(r.live_execution_authorized)

    def test_deterministic_digest_and_hand_provenance(self):
        self.assertEqual(handoff(), handoff())
        self.assertEqual(len(handoff().digest), 64)
        self.assertNotEqual(handoff().digest, handoff(hand_id=None).digest)

    def test_rejects_missing_exit_or_unready_entry(self):
        for changes in ({"exit_plan": None}, {"brain": brain(ready=False)}):
            with self.subTest(changes=changes):
                r = handoff(**changes)
                self.assertEqual(r.action, "WAIT")
                self.assertIsNone(r.stop)
                self.assertIsNone(r.target)

    def test_rejects_direction_and_stop_target_geometry(self):
        for e in (exit_plan("SELL", 2010., 1970.),
                  exit_plan("BUY", 2010., 2030.),
                  exit_plan("BUY", 1990., 1980.),
                  exit_plan("BUY", float("nan"), 2030.)):
            with self.subTest(exit=e):
                self.assertEqual(handoff(exit_plan=e).action, "WAIT")

    def test_rejects_forged_live_approval(self):
        cases = (
            {"brain": replace(brain(), live_risk_authorized=True)},
            {"brain": replace(brain(), research_only=False)},
            {"brain": replace(brain(),
                              proposal=replace(brain().proposal,
                                               live_risk_authorized=True))},
            {"exit_plan": replace(exit_plan(), live_execution_authorized=True)},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    handoff(**changes)

    def test_rejects_bad_identity_time_digest_and_prices(self):
        cases = (
            {"symbol": "NAS100"},
            {"entry": float("inf")},
            {"entry": float("nan")},
            {"source_digest": "missing"},
            {"as_of_utc": datetime(2026, 10, 14)},
            {"hand_id": "../untrusted"},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    handoff(**changes)

    def test_regime_mismatch_does_not_pass(self):
        old = brain()
        corrupted = replace(old, proposal=replace(
            old.proposal, strategy=Playbook.RANGE_FADE))
        r = handoff(brain=corrupted)
        self.assertEqual(r.action, "WAIT")
        self.assertIn("REGIME_PLAYBOOK_MISMATCH", r.reasons)

    def test_owner_view_has_no_command_path(self):
        view = handoff().owner_view()
        self.assertNotIn("order_send", view)
        self.assertNotIn("command", view)
        self.assertFalse(view["live_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
