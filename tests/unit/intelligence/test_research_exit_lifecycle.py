"""Broker specification boundary tests for non-executing Smart Exit reviews."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import unittest

from katarina.engines.adaptive_scalper import ResearchEntryPlan, ScalpSide
from katarina.intelligence.perception.adaptive_regime import MarketRead, MarketState, Playbook
from katarina.intelligence.cognition.adaptive_observation import BrainV2Observation
from katarina.intelligence.perception.structure_exit_plan import StructuralExitPlan
from katarina.intelligence.cognition.unified_research_handoff import research_handoff
from katarina.intelligence.lab.research_exit_lifecycle import review_offline_exit_lifecycle

CLOCK=datetime(2026,10,14,13,30,tzinfo=timezone.utc)


def source(side="BUY", ready=True):
    regime=MarketRead(MarketState.TREND_UP,Playbook.TREND_PULLBACK,
                      1,.7,"NORMAL",("closed",))
    plan=ResearchEntryPlan("XAUUSD",regime.state,regime.playbook,
                           ScalpSide(side),ready,("closed",),0.)
    brain=BrainV2Observation(regime,plan,None)
    sl,tp=((1990.,2030.) if side=="BUY" else (2010.,1970.))
    out=StructuralExitPlan(side,True,sl,tp,10.,3.,"swing","target",())
    return research_handoff(
        brain=brain,exit_plan=out,symbol="XAUUSD",entry=2000.,
        as_of_utc=CLOCK,source_digest="a"*64,hand_id="shadow-hand")


def review(**overrides):
    d=dict(
        source=source(), position_symbol="XAUUSD",
        position_owner="KATARINA", side="BUY",
        volume="0.05",broker_min_volume="0.01",
        broker_max_volume="100", broker_volume_step="0.01",
        bid="2000",ask="2000.05",
        broker_stop_distance="0.10",broker_freeze_distance="0.20",
        action="HOLD",observed_utc=CLOCK,
    )
    d.update(overrides)
    return review_offline_exit_lifecycle(**d)


class OfflineSmartExitLifecycleTests(unittest.TestCase):
    def test_hold_does_not_generate_orders(self):
        x=review()
        self.assertEqual(x.research_action,"HOLD_RESEARCH_ONLY")
        self.assertEqual(x.requested_action,"HOLD")
        self.assertEqual(x.volume_before,"0.05")
        self.assertIsNone(x.close_volume)
        self.assertFalse(x.live_execution_authorized)
        self.assertFalse(x.broker_costs_verified)
        self.assertFalse(x.owner_manual_positions_modified)
        self.assertEqual(x.orders_submitted,0)
        self.assertEqual(x.owner_view()["requested_action"],"HOLD")

    def test_full_close_is_feasibility_only(self):
        x=review(action="FULL")
        self.assertEqual(x.research_action,"EXIT_FEASIBLE_RESEARCH_ONLY")
        self.assertEqual((x.close_volume,x.volume_after),("0.05","0"))
        self.assertFalse(x.broker_acknowledgement_received)
        self.assertFalse(x.live_execution_authorized)

    def test_partial_close_honors_broker_step_and_remaining_minimum(self):
        x=review(action="PARTIAL",close_volume="0.02")
        self.assertEqual(x.research_action,"EXIT_FEASIBLE_RESEARCH_ONLY")
        self.assertEqual((x.close_volume,x.volume_after),("0.02","0.03"))
        bad=review(action="PARTIAL",close_volume="0.045")
        self.assertEqual(bad.research_action,"WAIT")
        self.assertIn("PARTIAL_VOLUME_OR_REMAINDER_BROKER_INVALID",
                      bad.blockers)

    def test_partial_cannot_leave_dust_or_be_full(self):
        for amount in ("0.045","0.05","0.06"):
            with self.subTest(amount=amount):
                r=review(action="PARTIAL",close_volume=amount)
                self.assertEqual(r.research_action,"WAIT")
        self.assertEqual(review(action="PARTIAL",close_volume="0.02",
                                broker_volume_step="0.02",
                                broker_min_volume="0.01").research_action,"WAIT")

    def test_buy_trailing_only_moves_protective_stop_forward(self):
        good=review(action="TRAIL",existing_sl="1990",proposed_sl="1995")
        self.assertEqual(good.research_action,"EXIT_FEASIBLE_RESEARCH_ONLY")
        self.assertEqual(good.proposed_stop,"1995")
        for old,new in (("1990","1989"),("1990","1990"),
                        ("1990","2000.0"),("1990","1999.9")):
            with self.subTest(old=old,new=new):
                self.assertEqual(review(action="TRAIL",existing_sl=old,
                                        proposed_sl=new).research_action,"WAIT")

    def test_sell_trailing_is_symmetric_and_respects_ask(self):
        args={"side":"SELL","source":source("SELL"),"action":"TRAIL",
              "existing_sl":"2010","proposed_sl":"2005"}
        self.assertEqual(review(**args).research_action,
                         "EXIT_FEASIBLE_RESEARCH_ONLY")
        for new in ("2011","2010","2000.1"):
            with self.subTest(new=new):
                self.assertEqual(review(**{**args,"proposed_sl":new}).research_action,
                                 "WAIT")

    def test_trailing_respects_broker_stop_and_freeze_distances(self):
        x=review(action="TRAIL",existing_sl="1990",proposed_sl="1999",
                 broker_freeze_distance="2")
        self.assertEqual(x.research_action,"WAIT")
        self.assertIn("BUY_TRAIL_NONPROTECTIVE_OR_BROKER_DISTANCE",x.blockers)

    def test_owner_manual_positions_are_never_actionable(self):
        for act,extra in (
            ("FULL",{}),
            ("PARTIAL",{"close_volume":"0.02"}),
            ("TRAIL",{"existing_sl":"1990","proposed_sl":"1995"}),
        ):
            with self.subTest(action=act):
                x=review(position_owner="OWNER_MANUAL",action=act,**extra)
                self.assertEqual(x.research_action,"WAIT")
                self.assertIn("MANUAL_OWNER_POSITION_PROTECTED",x.blockers)
                self.assertFalse(x.owner_manual_positions_modified)

    def test_unready_entry_never_makes_exit_feasible(self):
        x=review(action="FULL",source=source(ready=False))
        self.assertEqual(x.research_action,"WAIT")
        self.assertIn("ENTRY_RESEARCH_NOT_READY",x.blockers)

    def test_inconsistent_action_arguments_are_rejected(self):
        cases=(
            dict(action="HOLD",close_volume=".01"),
            dict(action="FULL",close_volume=".02"),
            dict(action="FULL",proposed_sl="1995"),
            dict(action="PARTIAL"),
            dict(action="TRAIL"),
            dict(action="TRAIL",close_volume=".01",proposed_sl="1995"),
        )
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(review(**case).research_action,"WAIT")

    def test_bad_volume_or_quote_evidence_is_rejected(self):
        cases=(
            dict(volume=".005"),
            dict(volume="0.055"),
            dict(broker_min_volume="0"),
            dict(broker_volume_step="0"),
            dict(broker_max_volume="0.02"),
            dict(bid="2001",ask="2000"),
            dict(bid=float("nan")),
            dict(ask=float("inf")),
            dict(broker_stop_distance=-1),
            dict(action="INVALID"),
            dict(position_owner="OTHER"),
            dict(position_symbol="NAS100"),
            dict(side="SELL"),
            dict(observed_utc=datetime(2026,10,14)),
        )
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    review(**case)

    def test_live_authority_flag_is_never_accepted(self):
        with self.assertRaisesRegex(ValueError,"invalid_exit_research_source"):
            review(source=replace(source(),live_execution_authorized=True))
        with self.assertRaisesRegex(ValueError,"invalid_exit_research_source"):
            review(source=replace(source(),strategy_promoted=True))

    def test_receipt_deterministic_and_never_sends_orders(self):
        a,b=review(action="PARTIAL",close_volume=".02"),review(
            action="PARTIAL",close_volume=".02")
        self.assertEqual(a,b)
        self.assertEqual(len(a.receipt_sha256),64)
        self.assertNotEqual(a.receipt_sha256,review(action="FULL").receipt_sha256)
        self.assertFalse(a.owner_view()["live_execution_authorized"])
        self.assertNotIn("order_send",a.owner_view())

    def test_modified_research_receipt_digest_is_not_trusted(self):
        for modified in (
            replace(source(), action="WAIT"),
            replace(source(), entry=2001.),
            replace(source(), target=2040.),
            replace(source(), reasons=("fake",)),
            replace(source(), source_digest="b"*64),
        ):
            with self.subTest(modified=modified):
                with self.assertRaises(ValueError):
                    review(action="FULL", source=modified)

    def test_future_entry_receipt_cannot_be_replayed_as_past_exit(self):
        late=source()
        with self.assertRaisesRegex(ValueError,"future_entry_research_evidence"):
            review(action="FULL",source=late,
                   observed_utc=CLOCK-timedelta(seconds=1))
        self.assertEqual(
            review(action="FULL", source=late,
                   observed_utc=CLOCK+timedelta(minutes=1)).research_action,
            "EXIT_FEASIBLE_RESEARCH_ONLY")

    def test_forged_hash_does_not_authorize_invalid_entry_geometry(self):
        def forge(**changes):
            item=replace(source(),**changes)
            fields=("observed_utc","source_digest","symbol","side",
                    "regime","playbook","action","entry","stop","target",
                    "reasons","hand_id")
            msg={k:getattr(item,k) for k in fields}
            dig=sha256(json.dumps(msg,sort_keys=True,
                                  separators=(",",":"),allow_nan=False
                                  ).encode()).hexdigest()
            return replace(item,digest=dig)
        for changes in (
            {"stop":2100.},
            {"target":1900.},
            {"action":"WAIT"},
            {"action":"LIVE_READY"},
            {"source_digest":"INVALID"},
            {"reasons":("fake-approval",)},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    review(action="FULL",source=forge(**changes))

    def test_wait_source_remains_wait_with_genuine_receipt(self):
        item=review(action="FULL",source=source(ready=False))
        self.assertEqual(item.research_action,"WAIT")
        self.assertIn("ENTRY_RESEARCH_NOT_READY",item.blockers)



if __name__=="__main__":
    unittest.main()
