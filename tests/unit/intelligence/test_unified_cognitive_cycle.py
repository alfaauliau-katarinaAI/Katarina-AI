"""End-to-end deterministic Unified Self-Evolving Brain memory and rollback."""
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from katarina.intelligence.shadow.prospective_shadow_book import ProspectiveShadowBook
from katarina.intelligence.cognition.unified_cognitive_cycle import (
    run_unified_cognitive_cycle,verify_cognitive_history,
    rollback_cognitive_research,
)

UTC=timezone.utc
START=datetime(2026,7,1,tzinfo=UTC)
AS_OF=START+timedelta(days=40)


def populate(db,days=30,*,include_sell=True):
    ProspectiveShadowBook(db)
    for day in range(days):
        for index in range(8):
            when=(START+timedelta(days=day,hours=index+1)).timestamp()
            buy=index%2==0 or not include_sell
            side="BUY" if buy else "SELL"
            symbol="XAUUSD.vx" if buy else "NAS100.vx"
            regime="TREND_UP" if buy else "TREND_DOWN"
            score=.85 if index%4 in (0,1) else .64
            value=(1.8 if score>.7 else -.6) if buy else -.8
            db.execute("""INSERT INTO prospective_shadow (
                symbol,bar_close,observed_at,tick_at,method,regime,side,
                bid,ask,entry,stop,target,risk,rr,evidence_score,
                official_news_verified,blockers,state,last_quote_epoch,
                exit_at,exit_price,reason,virtual_net_r
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
                symbol,datetime.fromtimestamp(when-300,UTC).isoformat(),
                when,when,"SWEEP",regime,side,
                100.,100.1,100.1,99.,103.,1.1,2.0,score,
                0,json.dumps(["cost_unverified"]),"VIRTUAL_QUOTED",
                when+900,when+900,101.,"SIMULATED_TIMED_EXIT_QUOTE",value))
    db.commit()


class UnifiedCognitionTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        populate(self.db)

    def tearDown(self):
        self.db.close()

    def test_full_closed_loop_outputs_every_agreed_cognitive_layer(self):
        output=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        self.assertEqual(output["ledger_status"],"LEARNED_AND_CHECKPOINTED")
        self.assertEqual(output["matured_observations"],240)
        self.assertEqual(len(output["episodic_memory"]),64)
        self.assertEqual(len(output["semantic_memory"]),2)
        self.assertEqual(len(output["world_model"]["cohorts"]),2)
        self.assertGreater(len(output["world_model"]["regime_transitions"]),0)
        self.assertEqual(len(output["curiosity_hypotheses"]),2)
        self.assertIn("causal_alternatives",output["curiosity_hypotheses"][0])
        self.assertIn("falsification",output["curiosity_hypotheses"][0])
        self.assertGreaterEqual(
            len(output["metacognition"]["uncertainty_flags"]),4)
        self.assertEqual(output["scientific_experiment_review"]["production_action"],
                         "WAIT")
        self.assertFalse(output["production_mutation_authorized"])
        self.assertFalse(output["real_execution_authorized"])
        self.assertEqual(output["orders_submitted"],0)
        self.assertTrue(output["source_snapshot_matches_active"])
        self.assertEqual(verify_cognitive_history(self.db)["events"],1)

    def test_no_overfitting_and_separate_buy_sell_experiments(self):
        output=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        cohorts={(c["symbol"],c["side"]):c
                 for c in output["curiosity_hypotheses"]}
        self.assertEqual(set(cohorts),{("XAUUSD.vx","BUY"),
                                        ("NAS100.vx","SELL")})
        self.assertEqual(
            cohorts[("NAS100.vx","SELL")]["scientific_experiment"],
            "TEST_DIFFERENT_METHOD_OR_WAIT")
        self.assertNotEqual(
            cohorts[("XAUUSD.vx","BUY")]["status"],
            "UNSTABLE_OR_NEGATIVE_QUOTE_EDGE")
        for group in cohorts.values():
            self.assertFalse(group["broker_execution_claim"])
            self.assertFalse(group["broker_costs_verified"])

    def test_repeated_learning_is_idempotent_without_new_mature_observation(self):
        a=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        b=run_unified_cognitive_cycle(
            self.db,as_of_utc=AS_OF+timedelta(minutes=1))
        self.assertEqual(b["ledger_status"],"ALREADY_LEARNED_NO_REWRITE")
        self.assertEqual(a["active_checkpoint_sha256"],
                         b["active_checkpoint_sha256"])
        self.assertEqual(verify_cognitive_history(self.db)["events"],1)

    def test_new_matured_outcome_updates_memory_preserving_old_evidence(self):
        a=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        when=(AS_OF+timedelta(minutes=10)).timestamp()
        self.db.execute("""INSERT INTO prospective_shadow (
            symbol,bar_close,observed_at,tick_at,method,regime,side,
            bid,ask,entry,stop,target,risk,rr,evidence_score,
            official_news_verified,blockers,state,last_quote_epoch,
            exit_at,exit_price,reason,virtual_net_r
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
            "XAUUSD.vx",datetime.fromtimestamp(when-300,UTC).isoformat(),
            when,when,"SWEEP","TREND_UP","BUY",100,100.1,100.1,99,103,
            1.1,2,.85,0,"[]","VIRTUAL_QUOTED",when+300,when+300,101,
            "SIMULATED_TIMED_EXIT_QUOTE",-1.0))
        self.db.commit()
        b=run_unified_cognitive_cycle(
            self.db,as_of_utc=AS_OF+timedelta(minutes=20))
        self.assertEqual(b["matured_observations"],241)
        self.assertNotEqual(a["active_checkpoint_sha256"],
                            b["active_checkpoint_sha256"])
        self.assertEqual(verify_cognitive_history(self.db)["events"],2)

    def test_curiosity_priority_changes_next_virtual_research_choice_only(self):
        from katarina.intelligence.shadow.prospective_shadow_book import ResearchHypothesis
        from katarina.intelligence.cognition.self_evolution_lab import (
            evaluate_shadow_self_evolution,derive_shadow_research_policy,
        )
        lab=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        research_policy=derive_shadow_research_policy(
            evaluate_shadow_self_evolution(self.db,as_of_utc=AS_OF))
        def proposal(symbol,side,score):
            return ResearchHypothesis(
                symbol=symbol,method="SWEEP",
                regime="TREND_UP" if side=="BUY" else "TREND_DOWN",
                side=side,closed_bar_at=AS_OF-timedelta(minutes=5),
                observed_at=AS_OF,bid=100.,ask=100.1,tick_at=AS_OF.timestamp(),
                stop=99. if side=="BUY" else 101.2,
                target=103. if side=="BUY" else 97.,
                evidence_score=score,blockers=("news_unverified",),
                official_news_verified=False,spread_atr=.05)
        xau=proposal("XAUUSD.vx","BUY",.85)
        nas=proposal("NAS100.vx","SELL",.95)
        # The learner does not change the risk gate or authorize an order.
        preferred={("XAUUSD.vx","SWEEP","BUY","TREND_UP"):3,
                   ("NAS100.vx","SWEEP","SELL","TREND_DOWN"):0}
        selected=ProspectiveShadowBook(self.db).propose(
            [nas,xau],AS_OF,research_policy=research_policy,
            research_priorities=preferred)
        self.assertEqual(selected["symbol"],"XAUUSD.vx")
        self.assertEqual(selected["mode"],"NO_REAL_ORDERS")
        self.assertFalse(lab["real_execution_authorized"])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM prospective_shadow WHERE state='OPEN'"
        ).fetchone()[0],1)

    def test_invalid_curiosity_priorities_are_rejected(self):
        book=ProspectiveShadowBook(self.db)
        for bad in (
            {("XAUUSD.vx","SWEEP","BUY","TREND_UP"):True},
            {("XAUUSD.vx","SWEEP","BUY","TREND_UP"):999},
            {("XAUUSD.vx","SWEEP","UNKNOWN","TREND_UP"):1},
        ):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError,"invalid_curiosity_priority"):
                    book.propose([],AS_OF,research_priorities=bad)
        self.assertFalse(book.summary()["counts"].get("OPEN",0))

    def test_corrupt_future_outcome_never_reaches_memory(self):
        future=(AS_OF+timedelta(hours=1)).timestamp()
        self.db.execute("UPDATE prospective_shadow SET exit_at=? WHERE id=1",
                        (future,))
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"cognitive_shadow_evidence_invalid"):
            run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        self.assertEqual(verify_cognitive_history(self.db)["events"],0)

    def test_stale_cognitive_clock_refuses_replay_without_changing_checkpoint(self):
        old=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        with self.assertRaisesRegex(ValueError,"cognitive_learning_clock_regressed"):
            run_unified_cognitive_cycle(
                self.db,as_of_utc=AS_OF-timedelta(minutes=1))
        self.assertEqual(verify_cognitive_history(self.db)["events"],1)
        self.assertEqual(
            verify_cognitive_history(self.db)["active_checkpoint_sha256"],
            old["active_checkpoint_sha256"])

    def test_stale_clock_refuses_newly_modified_outcome_checkpoint(self):
        original=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        self.db.execute(
            "UPDATE prospective_shadow SET virtual_net_r=-.9 WHERE side='BUY'")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"cognitive_learning_clock_regressed"):
            run_unified_cognitive_cycle(
                self.db,as_of_utc=AS_OF-timedelta(minutes=1))
        self.assertEqual(
            verify_cognitive_history(self.db)["active_checkpoint_sha256"],
            original["active_checkpoint_sha256"])

    def test_owner_rollback_cannot_backdate_a_newer_learning_event(self):
        first=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        self.db.execute(
            "UPDATE prospective_shadow SET virtual_net_r=-.9 WHERE side='BUY'")
        self.db.commit()
        run_unified_cognitive_cycle(
            self.db,as_of_utc=AS_OF+timedelta(minutes=10))
        before=verify_cognitive_history(self.db)
        with self.assertRaisesRegex(ValueError,"cognitive_rollback_clock_regressed"):
            rollback_cognitive_research(
                self.db,to_receipt_sha256=first["active_checkpoint_sha256"],
                as_of_utc=AS_OF+timedelta(minutes=5),owner_approved=True)
        self.assertEqual(before,verify_cognitive_history(self.db))

    def test_history_rejects_rewritten_backwards_timestamp_even_with_valid_receipt(self):
        from katarina.intelligence.cognition.unified_cognitive_cycle import _digest
        run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        self.db.execute(
            "UPDATE prospective_shadow SET virtual_net_r=-.9 WHERE side='BUY'")
        self.db.commit()
        run_unified_cognitive_cycle(
            self.db,as_of_utc=AS_OF+timedelta(minutes=10))
        row=self.db.execute(
            "SELECT seq,kind,observation_sha256,payload_json,previous_sha256 "
            "FROM katarina_cognitive_ledger WHERE seq=2").fetchone()
        earlier=(AS_OF-timedelta(minutes=5)).isoformat()
        mutated=dict(
            seq=row[0],kind=row[1],as_of_utc=earlier,
            observation_sha256=row[2],payload=json.loads(row[3]),
            previous_sha256=row[4],
        )
        self.db.execute(
            "UPDATE katarina_cognitive_ledger SET as_of_utc=?,entry_sha256=? "
            "WHERE seq=2",(earlier,_digest(mutated)))
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"cognitive_ledger_clock_regressed"):
            verify_cognitive_history(self.db)

    def test_readonly_preview_no_ledger_created(self):
        result=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF,
                                          persist=False)
        self.assertEqual(result["ledger_status"],"READ_ONLY_PREVIEW")
        self.assertEqual(verify_cognitive_history(self.db)["events"],0)
        self.assertEqual(result["orders_submitted"],0)

    def test_tamper_evidence_is_detected_and_new_learning_refused(self):
        run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        self.db.execute("""UPDATE katarina_cognitive_ledger
                           SET payload_json='{}' WHERE seq=1""")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"cognitive_ledger_chain_tampered"):
            verify_cognitive_history(self.db)
        with self.assertRaisesRegex(ValueError,"cognitive_ledger_chain_tampered"):
            run_unified_cognitive_cycle(
                self.db,as_of_utc=AS_OF+timedelta(minutes=1))

    def test_rollback_requires_owner_and_keeps_complete_append_only_audit(self):
        original=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        self.db.execute("""UPDATE prospective_shadow SET virtual_net_r=-.9
                           WHERE side='BUY'""")
        self.db.commit()
        new=run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        self.assertNotEqual(original["active_checkpoint_sha256"],
                            new["active_checkpoint_sha256"])
        with self.assertRaises(PermissionError):
            rollback_cognitive_research(
                self.db,to_receipt_sha256=original["active_checkpoint_sha256"],
                as_of_utc=AS_OF)
        reverted=rollback_cognitive_research(
            self.db,to_receipt_sha256=original["active_checkpoint_sha256"],
            as_of_utc=AS_OF,owner_approved=True)
        self.assertEqual(reverted["rollback"],"OWNER_RESEARCH_ROLLBACK_RECORDED")
        state=verify_cognitive_history(self.db)
        self.assertEqual(state["events"],3)
        self.assertEqual(state["active_checkpoint_sha256"],
                         original["active_checkpoint_sha256"])
        retry=run_unified_cognitive_cycle(
            self.db,as_of_utc=AS_OF+timedelta(minutes=1))
        self.assertEqual(retry["ledger_status"],
                         "OWNER_ROLLBACK_HOLD_NEW_RESEARCH")
        self.assertFalse(retry["source_snapshot_matches_active"])
        self.assertEqual(verify_cognitive_history(self.db)["events"],3)

    def test_corrupt_or_mismatched_schema_refused(self):
        run_unified_cognitive_cycle(self.db,as_of_utc=AS_OF)
        with self.assertRaisesRegex(ValueError,"unknown_or_nonlearn_checkpoint"):
            rollback_cognitive_research(
                self.db,to_receipt_sha256="3"*64,
                as_of_utc=AS_OF,owner_approved=True)
        with self.assertRaisesRegex(ValueError,"timezone_aware"):
            run_unified_cognitive_cycle(
                self.db,as_of_utc=datetime(2026,10,14))

    def test_restart_sqlite_history_reconstitutes_same_active_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path=Path(directory)/"brain.sqlite3"
            file_db=sqlite3.connect(db_path)
            try:
                populate(file_db,days=20)
                initial=run_unified_cognitive_cycle(file_db,as_of_utc=AS_OF)
            finally:
                file_db.close()
            again=sqlite3.connect(db_path)
            try:
                state=verify_cognitive_history(again)
                self.assertEqual(state["active_checkpoint_sha256"],
                                 initial["active_checkpoint_sha256"])
                repeat=run_unified_cognitive_cycle(
                    again,as_of_utc=AS_OF+timedelta(hours=1))
                self.assertEqual(repeat["ledger_status"],
                                 "ALREADY_LEARNED_NO_REWRITE")
                self.assertEqual(repeat["orders_submitted"],0)
            finally:
                again.close()

    def test_actual_brain_owns_observer_no_second_process(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[3]
        source=(root/"src/katarina/intelligence/cognition/unified_brain.py").read_text()
        cli=(root/"scripts/ai/run_contextual_market_observer.py").read_text()
        self.assertLess(source.index("self.shadow_book.settle("),
                        source.index("unified = self.run_unified_cognitive_cycle("))
        self.assertLess(source.index("unified = self.run_unified_cognitive_cycle("),
                        source.index("self.shadow_book.propose("))
        self.assertIn("UnifiedKatarinaBrain.observe_once(",cli)
        for text in (source,cli):
            self.assertNotIn("order_send(",text)
            self.assertNotIn("subprocess.Popen(",text)


if __name__=="__main__":
    unittest.main()
