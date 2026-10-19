"""The single research brain: perception, cognition and shared evidence memory.

Existing engines are capabilities, not independent workers. No broker gateway,
background scheduler, source rewrite or strategy promotion is available here.
Fast/Deep select existing retrieval budgets; they never change risk authority.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import sqlite3

from katarina.intelligence.market_decision_brain_v3 import MarketDecisionBrain
from katarina.intelligence.unified_cognitive_cycle import (
    run_unified_cognitive_cycle, verify_cognitive_history,
)
from katarina.intelligence.self_evolution_lab import (
    evaluate_shadow_self_evolution, derive_shadow_research_policy,
)
from katarina.intelligence.unified_adaptive_research_cycle import synthesize_offline_research
from katarina.memory.neuro_link import CognitiveEvidence, NeuroLinkMemory
from katarina.memory.store import MemoryStore
from katarina.intelligence.brain_runtime_control import BrainRuntimeControl
from katarina.contracts.runtime import RuntimeMode
from katarina.core.orchestrator import KatarinaOrchestrator, OrchestratorConfig
from katarina.engines.manual_risk import SharedAccountRiskEngine
from katarina.memory.runtime_state import RuntimeStatePersistence


class UnifiedKatarinaBrain:
    """One owner of the causal research path, with independent risk outside it."""

    def __init__(self, shadow_db: sqlite3.Connection, memory: MemoryStore):
        self.shadow_db = shadow_db
        self.memory = memory
        self._perception = MarketDecisionBrain()
        self._knowledge = NeuroLinkMemory(memory)
        self.control = BrainRuntimeControl(memory)
        self.core = KatarinaOrchestrator(OrchestratorConfig(RuntimeMode.TESTER, 32))
        self.manual_positions = SharedAccountRiskEngine()
        self.runtime_memory = RuntimeStatePersistence(memory)
        self.context_store = None
        self.quote_journal = None
        self.shadow_book = None
        self.observer = None

    @classmethod
    def research_once(cls, root, *, mode="fast"):
        """Resume local evidence research on any host, with no broker or network."""
        from pathlib import Path
        from katarina.host import inspect_host
        from katarina.intelligence.brain_observer import lock_worker
        from katarina.intelligence.public_context import ContextStore
        from katarina.intelligence.contextual_observation_journal import ContextDecisionJournal
        from katarina.intelligence.prospective_shadow_book import ProspectiveShadowBook
        if mode not in ("fast", "deep"):
            raise ValueError("invalid_research_mode")
        root = Path(root)
        host = inspect_host(root)
        if host["blockers"]:
            raise RuntimeError(",".join(host["blockers"]))
        lock = lock_worker(root)
        context = memory = brain = None
        try:
            context = ContextStore(root / "context.sqlite3")
            memory = MemoryStore(root / "cognitive-memory.sqlite3")
            brain = cls(context.db, memory)
            brain.quote_journal = ContextDecisionJournal(context.db)
            brain.shadow_book = ProspectiveShadowBook(context.db)
            brain.control.audit_phase("OBSERVING")
            result = brain.run_unified_cognitive_cycle(
                as_of_utc=datetime.now(timezone.utc), mode=mode)
            result["research_policy"] = result["research_policy"].to_dict()
            result["host_environment"] = host
            result["input_scope"] = "EXISTING_LOCAL_EVIDENCE_ONLY_NO_MARKET_FETCH"
            brain.control.audit_phase("COMPLETE")
            brain.control.checkpoint()
            return result
        except Exception as exc:
            if brain is not None:
                brain.control.audit_phase("BLOCKED", error=exc)
            raise
        finally:
            try:
                if memory is not None:
                    memory.close()
            finally:
                try:
                    if context is not None:
                        context.db.close()
                finally:
                    lock.close()

    @classmethod
    def observe_once(cls, root, *, broker=None, max_symbols=17, fetch_news=True):
        """Own exactly one bounded observation, including cleanup on every failure."""
        from pathlib import Path
        from katarina.intelligence.brain_observer import BrainObserver, lock_worker
        from katarina.intelligence.public_context import ContextStore
        from katarina.intelligence.contextual_observation_journal import ContextDecisionJournal
        from katarina.intelligence.prospective_shadow_book import ProspectiveShadowBook
        if type(max_symbols) is not int or not 1 <= max_symbols <= 17:
            raise ValueError("max_17_broker_markets")
        if type(fetch_news) is not bool:
            raise ValueError("invalid_news_fetch_mode")
        if broker is None:
            import MetaTrader5 as broker
        root = Path(root)
        lock = lock_worker(root)
        context = memory = brain = None
        try:
            if not broker.initialize():
                raise RuntimeError("BROKER_NOT_CONNECTED")
            terminal = broker.terminal_info()
            if terminal is None or terminal.trade_allowed:
                raise RuntimeError("FAIL_CLOSED_TRADING_MUST_BE_DISABLED")
            context = ContextStore(root / "context.sqlite3")
            memory = MemoryStore(root / "cognitive-memory.sqlite3")
            brain = cls(context.db, memory)
            brain.context_store = context
            brain.quote_journal = ContextDecisionJournal(context.db)
            brain.shadow_book = ProspectiveShadowBook(context.db)
            brain.observer = BrainObserver(brain, broker, root)
            brain.control.audit_phase("OBSERVING")
            result = brain.observer.run(max_symbols=max_symbols, fetch_news=fetch_news)
            brain.control.audit_phase("COMPLETE")
            brain.control.checkpoint()
            return result
        except Exception as exc:
            if brain is not None:
                brain.control.audit_phase("BLOCKED", error=exc)
            raise
        finally:
            # Nested cleanup means one failing close cannot leak the other owners.
            try:
                if memory is not None:
                    memory.close()
            finally:
                try:
                    if context is not None:
                        context.db.close()
                finally:
                    try:
                        broker.shutdown()
                    finally:
                        lock.close()

    def advance_shadow_cycle(self, *, now, latest_quotes, paper_hypotheses, quote_lookup):
        """Settle -> learn -> sample is one brain-owned sequence, never an order."""
        from katarina.intelligence.prospective_shadow_review import summarize
        from katarina.governance.multi_model_evolution_review import review_candidate
        if self.shadow_book is None or self.quote_journal is None:
            raise RuntimeError("brain_observer_resources_not_attached")
        trace = getattr(self, 'activity_trace', None)
        emit = trace.emit if trace is not None else lambda *a, **k: None
        emit('SETTLE','STARTED')
        resolved = self.quote_journal.resolve(latest_quotes, now, quote_lookup=quote_lookup)
        settled = self.shadow_book.settle(now=now, quotes=latest_quotes)
        emit('SETTLE','DONE')
        unified = self.run_unified_cognitive_cycle(as_of_utc=now)
        policy = unified["research_policy"]
        priorities = {
            (q["symbol"], q["method"], q["side"], q["regime"]):q["curiosity_priority"]
            for q in unified["cognition"]["curiosity_hypotheses"]
        } if policy.integrity_ok else {}
        selected = self.shadow_book.propose(
            paper_hypotheses, now, research_policy=policy, research_priorities=priorities)
        retrospective = summarize(self.shadow_db, now)
        return {
            "brain_architecture":unified["architecture"],
            "quote_markouts_resolved_this_cycle":resolved,
            "quote_markouts_use_past_only_broker_tick_history":True,
            "current_bidask_source":"BROKER_UTC_TICK_HISTORY_AS_OF_CLOCK",
            "quote_journal":self.quote_journal.summary(),
            "virtual_shadow_settled":settled,
            "self_evolution_lab":unified["self_evolution_lab"],
            "unified_cognitive_cycle":unified["cognition"],
            "neuro_link_memory":unified["knowledge_memory"],
            "shadow_research_policy":policy.to_dict(),
            "virtual_shadow_selection":selected,
            "virtual_shadow_summary":self.shadow_book.summary(),
            "self_evolution_model_review":review_candidate(unified["self_evolution_lab"]).to_dict(),
            "virtual_memory_cohorts":sorted(retrospective["groups"], key=lambda g:-g["complete"])[:12],
            "virtual_memory_total_cohorts":len(retrospective["groups"]),
            "virtual_memory_cannot_authorize_real_trading":True,
            "virtual_shadow_not_executed":True,
        }

    def acknowledge_observation(self, broker, report):
        """Return a WAIT receipt to Hands; never sends an executable instruction."""
        from hashlib import sha256
        import json
        import time
        import uuid
        feedback = getattr(broker, 'brain_feedback', None)
        if feedback is None:
            return {"status": "NOT_SUPPORTED", "orders_submitted": 0}
        receipts = []
        for symbol, card in report['symbols'].items():
            now = time.time()
            message = {"feedback_id": uuid.uuid4().hex, "symbol": symbol,
                       "action": "WAIT_LIVE_OFF", "created_at": now, "expires_at": now + 20,
                       "plan_sha256": sha256(json.dumps(card, sort_keys=True,
                                                       allow_nan=False).encode()).hexdigest()}
            receipt = feedback(message)
            digest = sha256(json.dumps(message, sort_keys=True, allow_nan=False).encode()).hexdigest()
            if (not isinstance(receipt, dict)
                    or receipt.get('feedback_id') != message['feedback_id']
                    or receipt.get('message_sha256') != digest
                    or receipt.get('status') != 'ACKNOWLEDGED_LIVE_OFF'
                    or type(receipt.get('orders_submitted')) is not int
                    or receipt['orders_submitted'] != 0
                    or receipt.get('live_execution_authorized') is not False):
                raise RuntimeError('BRAIN_FEEDBACK_ACK_REJECTED')
            self.memory.append_operational_event('brain_hands_feedback_v1', receipt)
            receipts.append(receipt)
        return {"status": "ACKNOWLEDGED_LIVE_OFF", "receipts": receipts,
                "orders_submitted": 0, "broker_order_execution_verified": False}

    def inspect_foundation(self, broker, report, *, expected_symbols):
        """Internal monitor consumes read-only external facts; never initializes capital."""
        from katarina.intelligence.broker_account_monitor import inspect_broker_account
        from katarina.intelligence.broker_history_coverage import inspect_history
        from katarina.intelligence.official_cache_provenance import inspect_cached_official_sources
        from katarina.intelligence.foundation_readiness import assess_foundation
        monitor = inspect_broker_account(broker, observed_at_utc=datetime.now(timezone.utc))
        if not monitor["algo_trading_off"]:
            raise RuntimeError("FAIL_CLOSED_TRADING_PERMISSION_CHANGED")
        result = {
            "broker_account_monitor":monitor,
            "broker_history_coverage":inspect_history(broker, as_of_utc=datetime.now(timezone.utc)),
            "official_cache_integrity":inspect_cached_official_sources(
                self.shadow_db, as_of_utc=datetime.now(timezone.utc)),
            "brain_runtime":self.control.snapshot(),
        }
        result["foundation_readiness"] = assess_foundation(
            {**report, **result}, expected_symbols=expected_symbols)
        return result

    def publish_observation(self, root, report):
        """One atomic publication point; a research report cannot arm delivery."""
        from katarina.intelligence.brain_observer import publish
        if (report.get("orders_submitted") != 0
                or report.get("live_execution_authorized") is not False
                or report.get("production_execution") is not False):
            raise RuntimeError("brain_observation_safety_violation")
        # The snapshot is COMPLETE only if this atomic publication succeeds.
        report["brain_runtime"] = {**self.control.snapshot(), "phase":"COMPLETE"}
        publish(root, report)

    def prepare_research(self):
        from katarina.intelligence.contextual_observation_journal import ContextDecisionJournal
        from katarina.intelligence.prospective_shadow_book import ProspectiveShadowBook
        if self.quote_journal is None:
            self.quote_journal = ContextDecisionJournal(self.shadow_db)
        if self.shadow_book is None:
            self.shadow_book = ProspectiveShadowBook(self.shadow_db)

    def observe_connected_market(self, root, broker, *, max_symbols=3, fetch_news=False):
        """A dialog-owned sensor pass reuses its brain, DB and already-held host lock."""
        from katarina.intelligence.brain_observer import BrainObserver
        if self.context_store is None:
            raise RuntimeError('brain_context_store_required')
        if type(max_symbols) is not int or not 1 <= max_symbols <= 17:
            raise ValueError('max_17_broker_markets')
        from pathlib import Path
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        try:
            if not broker.initialize():
                raise RuntimeError('BROKER_NOT_CONNECTED')
            terminal = broker.terminal_info()
            if terminal is None or terminal.trade_allowed:
                raise RuntimeError('FAIL_CLOSED_TRADING_MUST_BE_DISABLED')
            self.prepare_research()
            self.observer = BrainObserver(self, broker, root)
            self.control.audit_phase('OBSERVING')
            result = self.observer.run(max_symbols=max_symbols, fetch_news=fetch_news)
            self.control.audit_phase('COMPLETE')
            self.control.checkpoint()
            return result
        except Exception as exc:
            self.control.audit_phase('BLOCKED', error=exc)
            raise
        finally:
            try:
                broker.shutdown()
            finally:
                self.observer = None

    def converse(self, text, **options):
        """Dialog, recall and bounded tools share this brain and its memory."""
        from katarina.intelligence.assistant_cycle import run_turn
        return run_turn(self, text, **options)

    def review_delivery(self, plan_id, request, *, governor=None):
        result = self.control.delivery.inspect(plan_id, request, governor)
        self.memory.append_operational_event("single_brain_delivery_review_v1", result)
        return result

    def preview_recovery(self, plan, *, side, current_stop, position_origin,
                         current_volume, volume_step):
        """Use the existing recovery engine internally; return unsent intents only."""
        self.control.recovery.apply_plan(
            plan, side=side, current_stop=current_stop, position_origin=position_origin)
        commands = self.control.recovery.reconcile(
            plan.position_id, current_volume=current_volume,
            current_stop=current_stop, volume_step=volume_step)
        self.control.checkpoint()
        return {"commands":[asdict(c) for c in commands], "orders_submitted":0,
                "delivery":"DISABLED", "live_execution_authorized":False}

    def market_atr(self, rows):
        """Delegate observed volatility to the existing perception engine."""
        return self._perception._atr(rows)

    def evaluate_contextually(self, **evidence):
        # Preserve the existing market decision semantics and hard controls.
        return self._perception.evaluate_contextually(**evidence)

    def synthesize_entry_exit(self, **evidence):
        return synthesize_offline_research(self.shadow_db, **evidence)

    def run_unified_cognitive_cycle(
        self, *, as_of_utc: datetime, persist: bool = True,
        mode: str = "fast", context_tags: tuple[str, ...] = (),
    ) -> dict:
        if mode not in ("fast", "deep"):
            raise ValueError("invalid_single_brain_recall_mode")
        if (not isinstance(as_of_utc, datetime) or as_of_utc.tzinfo is None
                or as_of_utc.utcoffset() is None):
            raise ValueError("timezone_aware_cognitive_clock_required")
        clock = as_of_utc.astimezone(timezone.utc)
        trace = getattr(self, 'activity_trace', None)
        emit = trace.emit if trace is not None else lambda *a, **k: None
        emit('CHECKPOINT','STARTED')
        # Verify the Owner's checkpoint before learning, including read-only runs.
        history = verify_cognitive_history(self.shadow_db)
        if history["last_event_as_of_utc"] is not None:
            last = datetime.fromisoformat(history["last_event_as_of_utc"])
            if last > clock:
                raise ValueError("cognitive_learning_clock_regressed")
        emit('CHECKPOINT','DONE')
        emit('LEARNING_REVIEW','STARTED')
        cognition = run_unified_cognitive_cycle(
            self.shadow_db, as_of_utc=clock, persist=persist)
        emit('LEARNING_REVIEW','DONE')
        emit('RESEARCH','STARTED')
        lab = evaluate_shadow_self_evolution(self.shadow_db, as_of_utc=clock)
        policy = derive_shadow_research_policy(lab)
        emit('RESEARCH','DONE')
        blockers = []
        if (cognition.get("source_snapshot_matches_active") is False
                or history["last_event_kind"] == "ROLLBACK"):
            blockers.append("OWNER_CHECKPOINT_HOLD")
        if (not persist and history["events"] and
                history["active_observation_sha256"] != cognition["observation_sha256"]):
            blockers.append("ACTIVE_CHECKPOINT_NOT_CURRENT_SNAPSHOT")
        tags = set(context_tags)
        inserted = 0
        emit('MEMORY_WRITE','STARTED')
        if not blockers:
            for row in cognition["episodic_memory"]:
                # Quote markouts never become independently validated broker P/L.
                if row["status"] != "VIRTUAL_QUOTED":
                    continue
                row_tags = tuple(str(row[k]) for k in ("symbol", "method", "side", "regime"))
                tags.update(row_tags)
                if not persist:
                    continue
                observed = int(row["observed"] * 1_000_000_000)
                # First availability is this ingestion, never a backdated exit.
                evidence_id = "shadow:" + str(row["id"])
                previous = self.memory.load_operational_event("neuro_link:" + evidence_id)
                known = (previous["payload"]["known_ns"] if previous else
                         int(clock.timestamp() * 1_000_000_000))
                if known <= observed:
                    raise ValueError("noncausal_neuro_link_quote_outcome")
                evidence = CognitiveEvidence(
                    evidence_id=evidence_id,
                    event_group_id="shadow:" + str(row["id"]),
                    observed_ns=observed, known_ns=known,
                    hypothesis="quote association: " + str(row["method"]),
                    tags=row_tags, decision=str(row["side"]),
                    outcome_net_r=row["net_r"], quality="OBSERVED",
                    reason="VIRTUAL_QUOTE_MARKOUT_NOT_BROKER_EXECUTION",
                )
                inserted += int(self._knowledge.remember(evidence))
        emit('MEMORY_WRITE','DONE',count=inserted)
        emit('RECALL','STARTED')
        recall = self._knowledge.recall(
            tuple(sorted(tags)), as_of_ns=int(clock.timestamp() * 1_000_000_000), mode=mode)
        emit('RECALL','DONE',count=recall.records_considered)
        if recall.history_truncated:
            blockers.append("KNOWLEDGE_RECALL_HISTORY_TRUNCATED")
        if blockers:
            policy = replace(policy, integrity_ok=False)
        # Rollback must quarantine recalled associations as well as future sampling.
        knowledge = asdict(recall)
        if blockers:
            knowledge["links"] = []
        return {
            "architecture":"SINGLE_COGNITIVE_BRAIN",
            "specialist_workers":0,
            "cognition":cognition, "self_evolution_lab":lab,
            "research_policy":policy,
            "knowledge_memory":{
                **knowledge, "mode":mode, "records_inserted":inserted,
                "quarantine_reasons":sorted(set(blockers)),
                "shared_memory":True,
                "import_scope":"BOUNDED_EPISODIC_EXAMPLES_NOT_FULL_HISTORY",
            },
            "orders_submitted":0, "live_execution_authorized":False,
        }
