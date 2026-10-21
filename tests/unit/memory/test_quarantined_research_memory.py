"""Safe persistence/learning quarantine of untrusted Entry/Exit research."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from katarina.engines.adaptive_scalper import ResearchEntryPlan, ScalpSide
from katarina.intelligence.perception.adaptive_regime import MarketRead, MarketState, Playbook
from katarina.intelligence.cognition.adaptive_observation import BrainV2Observation
from katarina.intelligence.perception.structure_exit_plan import StructuralExitPlan
from katarina.intelligence.cognition.unified_research_handoff import research_handoff
from katarina.memory.quarantined_research_memory import (
    append_quarantined_research, read_quarantined_research,
)

CLOCK = datetime(2026,10,14,13,30,tzinfo=timezone.utc)


def receipt(hand="shadow-hand", *, source="a", side="BUY", at=CLOCK):
    regime=MarketRead(MarketState.TREND_UP, Playbook.TREND_PULLBACK,
                      1,.7,"NORMAL",("closed_bar",))
    plan=ResearchEntryPlan("XAUUSD", regime.state, regime.playbook,
                           ScalpSide(side), True,("closed_bar",),0.0)
    brain=BrainV2Observation(regime,plan,None)
    stop,target=((1990.,2030.) if side=="BUY" else (2010.,1970.))
    out=StructuralExitPlan(side,True,stop,target,10.,3.,"swing","target",())
    return research_handoff(
        brain=brain,exit_plan=out,symbol="XAUUSD",entry=2000.,
        as_of_utc=at,source_digest=source*64,hand_id=hand)


class ResearchMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"quarantine.sqlite3"
        self.db=sqlite3.connect(self.path)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_empty_read_does_not_create_database_table(self):
        result=read_quarantined_research(self.db,as_of_utc=CLOCK)
        self.assertEqual(result["recorded_receipts"],0)
        self.assertFalse(result["source_origin_authenticated"])
        self.assertFalse(result["live_execution_authorized"])
        self.assertIsNone(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name="
            "'katarina_quarantined_research_memory'").fetchone())

    def test_append_and_same_content_replay_are_idempotent(self):
        item=receipt()
        first=append_quarantined_research(
            self.db,receipt=item,inspected_at_utc=CLOCK)
        second=append_quarantined_research(
            self.db,receipt=item,inspected_at_utc=CLOCK)
        self.assertTrue(first.inserted)
        self.assertFalse(second.inserted)
        self.assertEqual(first.receipt_sha256,second.receipt_sha256)
        r=read_quarantined_research(self.db,as_of_utc=CLOCK)
        self.assertEqual(r["recorded_receipts"],1)
        self.assertEqual(r["reported_source_fingerprints"],1)
        self.assertEqual(r["reused_source_symbols"],())
        self.assertFalse(r["independent_alpha_samples_proven"])
        self.assertFalse(r["may_promote_strategy"])
        self.assertEqual(r["orders_submitted"],0)
        self.assertEqual(r["owner_reports"][0]["hand_trust"],
                         "UNVERIFIED_TELEMETRY")

    def test_restart_preserves_quarantine_but_never_promotes(self):
        append_quarantined_research(
            self.db,receipt=receipt(),inspected_at_utc=CLOCK)
        self.db.close()
        self.db=sqlite3.connect(self.path)
        view=read_quarantined_research(self.db,as_of_utc=CLOCK)
        self.assertEqual(view["recorded_receipts"],1)
        self.assertEqual(view["status"],
                         "QUARANTINED_UNAUTHENTICATED_RESEARCH_MEMORY")
        self.assertFalse(view["live_execution_authorized"])

    def test_two_hands_same_source_are_one_reported_source_not_two_alpha_samples(self):
        for hand in ("hand-1","hand-2"):
            append_quarantined_research(
                self.db,receipt=receipt(hand),inspected_at_utc=CLOCK)
        view=read_quarantined_research(self.db,as_of_utc=CLOCK)
        self.assertEqual(view["recorded_receipts"],2)
        self.assertEqual(view["reported_source_fingerprints"],1)
        self.assertEqual(view["reused_source_symbols"],("XAUUSD",))
        self.assertEqual(view["next_curiosity_tasks"],({
            "symbol":"XAUUSD",
            "experiment":"COLLECT_NEW_INDEPENDENT_CAUSAL_QUOTE_SOURCES",
            "production_action":"WAIT",
        },))
        self.assertFalse(view["independent_alpha_samples_proven"])

    def test_distinct_reported_sources_are_still_unauthenticated(self):
        for hand,source in (("hand-1","a"),("hand-2","f")):
            append_quarantined_research(
                self.db,receipt=receipt(hand,source=source),
                inspected_at_utc=CLOCK)
        view=read_quarantined_research(self.db,as_of_utc=CLOCK)
        self.assertEqual(view["reported_source_fingerprints"],2)
        self.assertEqual(view["reused_source_symbols"],())
        self.assertFalse(view["independent_alpha_samples_proven"])

    def test_asof_read_excludes_future_known_observation(self):
        append_quarantined_research(
            self.db,receipt=receipt(at=CLOCK),inspected_at_utc=CLOCK)
        before=read_quarantined_research(
            self.db,as_of_utc=CLOCK-timedelta(seconds=1))
        self.assertEqual(before["recorded_receipts"],0)
        self.assertEqual(read_quarantined_research(
            self.db,as_of_utc=CLOCK)["recorded_receipts"],1)

    def test_future_report_cannot_modify_database(self):
        with self.assertRaisesRegex(ValueError,"future_hand_observation"):
            append_quarantined_research(
                self.db,receipt=receipt(),inspected_at_utc=CLOCK-timedelta(minutes=1))
        self.assertIsNone(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name="
            "'katarina_quarantined_research_memory'").fetchone())

    def test_invalid_or_spoofed_live_report_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"untrusted_hand_execution_claim"):
            append_quarantined_research(
                self.db,receipt=replace(
                    receipt(),live_execution_authorized=True),
                inspected_at_utc=CLOCK)

    def test_one_hand_rewriting_same_timestamp_is_conflict(self):
        append_quarantined_research(
            self.db,receipt=receipt(source="a"),inspected_at_utc=CLOCK)
        with self.assertRaisesRegex(ValueError,"idempotency_conflict"):
            append_quarantined_research(
                self.db,receipt=receipt(source="f"),inspected_at_utc=CLOCK)
        self.assertEqual(read_quarantined_research(
            self.db,as_of_utc=CLOCK)["recorded_receipts"],1)

    def test_payload_tampering_is_detected_even_when_sqlite_integrity_good(self):
        append_quarantined_research(
            self.db,receipt=receipt(),inspected_at_utc=CLOCK)
        with self.db:
            self.db.execute(
                "DROP TRIGGER katarina_quarantined_research_memory_no_update")
            self.db.execute(
                "UPDATE katarina_quarantined_research_memory "
                "SET payload_json='{}'")
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        with self.assertRaisesRegex(ValueError,"digest_mismatch"):
            read_quarantined_research(self.db,as_of_utc=CLOCK)
        with self.assertRaisesRegex(ValueError,"digest_mismatch"):
            append_quarantined_research(
                self.db,receipt=receipt(),inspected_at_utc=CLOCK)

    def test_append_only_sqlite_triggers_reject_update_and_delete(self):
        append_quarantined_research(
            self.db,receipt=receipt(),inspected_at_utc=CLOCK)
        for sql in (
            "UPDATE katarina_quarantined_research_memory SET symbol='FAKE'",
            "DELETE FROM katarina_quarantined_research_memory",
        ):
            with self.subTest(sql=sql):
                with self.assertRaises(sqlite3.IntegrityError):
                    with self.db:
                        self.db.execute(sql)

    def test_memory_view_preserves_connection_row_factory(self):
        self.db.row_factory=sqlite3.Row
        append_quarantined_research(
            self.db,receipt=receipt(),inspected_at_utc=CLOCK)
        view=read_quarantined_research(self.db,as_of_utc=CLOCK)
        self.assertEqual(view["recorded_receipts"],1)
        self.assertIs(self.db.row_factory,sqlite3.Row)

    def test_quarantine_has_no_owner_commands(self):
        append_quarantined_research(
            self.db,receipt=receipt(),inspected_at_utc=CLOCK)
        view=read_quarantined_research(self.db,as_of_utc=CLOCK)
        self.assertNotIn("order_send",view)
        self.assertNotIn("command",view)
        self.assertFalse(view["live_execution_authorized"])


if __name__=="__main__":
    unittest.main()
