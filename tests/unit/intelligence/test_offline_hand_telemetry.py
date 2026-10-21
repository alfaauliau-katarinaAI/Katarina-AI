"""Cloud Hand offline fan-in must never become Owner command authority."""
from dataclasses import replace
from hashlib import sha256
import json
from datetime import datetime, timedelta, timezone
import unittest

from katarina.engines.adaptive_scalper import ResearchEntryPlan, ScalpSide
from katarina.intelligence.perception.adaptive_regime import MarketRead, MarketState, Playbook
from katarina.intelligence.cognition.adaptive_observation import BrainV2Observation
from katarina.intelligence.perception.structure_exit_plan import StructuralExitPlan
from katarina.intelligence.cognition.unified_research_handoff import research_handoff
from katarina.intelligence.lab.offline_hand_telemetry import consolidate_hand_reports

CLOCK = datetime(2026, 10, 14, 13, 30, tzinfo=timezone.utc)


def receipt(hand, side="BUY"):
    regime = MarketRead(MarketState.TREND_UP, Playbook.TREND_PULLBACK,
                        1, .7, "NORMAL", ("closed",))
    plan = ResearchEntryPlan("XAUUSD", regime.state, regime.playbook,
                             ScalpSide(side), True, ("closed",), 0.)
    brain = BrainV2Observation(regime, plan, None)
    stop, target = (1990., 2030.) if side == "BUY" else (2010., 1970.)
    out = StructuralExitPlan(side, True, stop, target, 10., 3.,
                             "swing", "target", ())
    return research_handoff(
        brain=brain, exit_plan=out, symbol="XAUUSD", entry=2000.,
        source_digest="f" * 64, as_of_utc=CLOCK, hand_id=hand)


def rehashed(report, **changes):
    """Local test-only forged SHA proves checksum cannot authenticate a Hand."""
    modified = replace(report, **changes)
    keys = ("observed_utc", "source_digest", "symbol", "side",
            "regime", "playbook", "action", "entry", "stop", "target",
            "reasons", "hand_id")
    payload = {key: getattr(modified, key) for key in keys}
    digest = sha256(json.dumps(
        payload, allow_nan=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    return replace(modified, digest=digest)


class OfflineHandsTests(unittest.TestCase):
    def test_two_hands_have_deterministic_read_only_owner_view(self):
        a, b = receipt("z-hand"), receipt("a-hand")
        x = consolidate_hand_reports([a, b], inspected_at_utc=CLOCK)
        y = consolidate_hand_reports([b, a], inspected_at_utc=CLOCK)
        self.assertEqual(x, y)
        self.assertEqual(len(x.reports), 2)
        self.assertEqual(x.reports[0]["hand_id"], "a-hand")
        self.assertEqual(x.shared_source_symbols, ("XAUUSD",))
        self.assertEqual(
            x.research_integrity_flags[0]["flags"],
            ("UNAUTHENTICATED_HAND_ORIGIN",
             "REUSED_CAUSAL_SOURCE_NOT_INDEPENDENT"))
        self.assertFalse(x.cloud_authenticated)
        self.assertFalse(x.live_execution_authorized)
        self.assertEqual(x.orders_submitted, 0)
        self.assertEqual(x.owner_controls, "READ_ONLY_NO_REMOTE_COMMANDS")

    def test_opposing_hands_surface_conflict_not_action(self):
        x = consolidate_hand_reports(
            [receipt("hand-buy"), receipt("hand-sell", side="SELL")],
            inspected_at_utc=CLOCK)
        self.assertEqual(x.symbol_conflicts, ("XAUUSD",))
        self.assertIn("CONFLICTING_RESEARCH_SIDES",
                      x.research_integrity_flags[0]["flags"])
        self.assertFalse(x.owner_view()["live_execution_authorized"])

    def test_duplicate_hand_symbol_is_rejected(self):
        one = receipt("a-hand")
        with self.assertRaisesRegex(ValueError, "duplicate_hand_symbol_report"):
            consolidate_hand_reports([one, one], inspected_at_utc=CLOCK)

    def test_unidentified_hands_are_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "missing_hand_identity"):
            consolidate_hand_reports([receipt(None)], inspected_at_utc=CLOCK)

    def test_rejects_future_report_and_naive_inspection_clock(self):
        with self.assertRaisesRegex(ValueError, "future_hand_observation"):
            consolidate_hand_reports([receipt("a-hand")],
                                     inspected_at_utc=CLOCK-timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "owner_review_clock_invalid"):
            consolidate_hand_reports([], inspected_at_utc=datetime(2026,10,14))

    def test_rejects_modified_receipt_even_if_other_fields_well_formed(self):
        one = receipt("a-hand")
        with self.assertRaisesRegex(ValueError, "hand_report_integrity_mismatch"):
            consolidate_hand_reports(
                [replace(one, entry=2001.)], inspected_at_utc=CLOCK)

    def test_no_source_authentication_is_claimed(self):
        x = consolidate_hand_reports([], inspected_at_utc=CLOCK)
        self.assertEqual(x.reports, ())
        self.assertFalse(x.cloud_authenticated)
        self.assertEqual(x.symbol_conflicts, ())
        self.assertEqual(x.shared_source_symbols, ())
        self.assertEqual(x.research_integrity_flags, ())
        self.assertNotIn("command", x.owner_view())
        self.assertNotIn("order_send", x.owner_view())

    def test_rejects_any_attempted_live_or_promotion_claim(self):
        for updates in (
            {"live_execution_authorized": True},
            {"strategy_promoted": True},
            {"orders_submitted": 1},
            {"research_only": False},
        ):
            with self.subTest(updates=updates):
                with self.assertRaisesRegex(ValueError, "untrusted_hand_execution_claim"):
                    consolidate_hand_reports(
                        [replace(receipt("a-hand"), **updates)],
                        inspected_at_utc=CLOCK)

    def test_distinct_source_hashes_are_not_wrongly_deduplicated(self):
        original = receipt("first")
        second = rehashed(receipt("second"), source_digest="e" * 64)
        view = consolidate_hand_reports(
            [original, second], inspected_at_utc=CLOCK)
        self.assertEqual(view.shared_source_symbols, ())
        # Different checksums are not authentication or proof of independence.
        self.assertEqual(view.research_integrity_flags[0]["flags"],
                         ("UNAUTHENTICATED_HAND_ORIGIN",))
        self.assertFalse(view.cloud_authenticated)

    def test_wait_report_is_not_a_positive_research_candidate(self):
        waiting = rehashed(receipt("waiter"), action="WAIT",
                           stop=None, target=None, reasons=("NO_EXIT",))
        view = consolidate_hand_reports(
            [waiting], inspected_at_utc=CLOCK)
        self.assertEqual(view.research_integrity_flags, ())
        self.assertEqual(view.reports[0]["action"], "WAIT")

    def test_rehashed_unsafe_action_is_rejected_without_trusting_hash(self):
        for changes, error in (
            ({"action": "LIVE_READY"}, "untrusted_hand_action"),
            ({"side": "HEDGE"}, "untrusted_hand_side"),
            ({"hand_id": "../injected"}, "untrusted_hand_identifier"),
            ({"source_digest": "bad"}, "invalid_hand_source_identity"),
            ({"entry": -1.0}, "invalid_hand_entry"),
            ({"action": "WAIT"}, "untrusted_wait_research_state"),
            ({"stop": 2100.0}, "untrusted_buy_exit_geometry"),
            ({"reasons": ("fake-blocker",)}, "untrusted_candidate_research_state"),
        ):
            with self.subTest(changes=changes):
                forged = rehashed(receipt("forged"), **changes)
                with self.assertRaisesRegex(ValueError, error):
                    consolidate_hand_reports(
                        [forged], inspected_at_utc=CLOCK)

    def test_invalid_telemetry_collection_refused(self):
        for item in (None, "not a collection", [object()]):
            with self.subTest(item=item):
                with self.assertRaises(ValueError):
                    consolidate_hand_reports(item, inspected_at_utc=CLOCK)


if __name__ == "__main__":
    unittest.main()
