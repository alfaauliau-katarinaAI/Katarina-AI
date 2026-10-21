"""One runtime, shared causal memory, restart and independent safety boundaries."""
from datetime import timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest

from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.intelligence.cognition.unified_cognitive_cycle import (
    rollback_cognitive_research, verify_cognitive_history,
)
from katarina.memory import MemoryStore
from tests.unit.intelligence.test_unified_cognitive_cycle import populate, START, AS_OF


class SingleBrainRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = sqlite3.connect(Path(self.temp.name) / 'shadow.sqlite3')
        populate(self.db)
        self.memory_path = Path(self.temp.name) / 'knowledge.sqlite3'
        self.memory = MemoryStore(self.memory_path)
        self.brain = UnifiedKatarinaBrain(self.db, self.memory)

    def tearDown(self):
        self.memory.close()
        self.db.close()
        self.temp.cleanup()

    def test_closed_quote_outcomes_reach_same_memory_without_broker_promotion(self):
        result = self.brain.run_unified_cognitive_cycle(as_of_utc=AS_OF)
        knowledge = result['knowledge_memory']
        self.assertGreater(knowledge['records_inserted'], 0)
        self.assertTrue(knowledge['links'])
        self.assertTrue(all(link['validated_events'] == 0 and link['quarantined']
                            for link in knowledge['links']))
        self.assertEqual(result['specialist_workers'], 0)
        self.assertFalse(result['live_execution_authorized'])
        self.assertEqual(result['orders_submitted'], 0)

    def test_fast_and_deep_reuse_checkpoint_and_memory_after_restart(self):
        fast = self.brain.run_unified_cognitive_cycle(as_of_utc=AS_OF)
        self.memory.close()
        self.memory = MemoryStore(self.memory_path)
        restarted = UnifiedKatarinaBrain(self.db, self.memory)
        deep = restarted.run_unified_cognitive_cycle(
            as_of_utc=AS_OF + timedelta(minutes=1), mode='deep')
        self.assertEqual(deep['knowledge_memory']['records_inserted'], 0)
        self.assertEqual(fast['knowledge_memory']['links'], deep['knowledge_memory']['links'])
        self.assertEqual(fast['cognition']['active_checkpoint_sha256'],
                         deep['cognition']['active_checkpoint_sha256'])
        self.assertEqual(verify_cognitive_history(self.db)['events'], 1)

    def test_preview_does_not_write_either_database(self):
        changes = self.db.total_changes, self.memory._conn.total_changes
        self.brain.run_unified_cognitive_cycle(as_of_utc=AS_OF, persist=False)
        self.assertEqual(changes, (self.db.total_changes, self.memory._conn.total_changes))

    def test_owner_rollback_quarantines_knowledge_and_virtual_sampling(self):
        first = self.brain.run_unified_cognitive_cycle(as_of_utc=START + timedelta(days=10))
        self.brain.run_unified_cognitive_cycle(as_of_utc=AS_OF)
        rollback_cognitive_research(
            self.db, to_receipt_sha256=first['cognition']['active_checkpoint_sha256'],
            as_of_utc=AS_OF + timedelta(minutes=1), owner_approved=True)
        result = self.brain.run_unified_cognitive_cycle(
            as_of_utc=AS_OF + timedelta(minutes=2), persist=False)
        self.assertFalse(result['research_policy'].integrity_ok)
        self.assertEqual(result['knowledge_memory']['links'], [])
        self.assertIn('OWNER_CHECKPOINT_HOLD', result['knowledge_memory']['quarantine_reasons'])

    def test_tampered_knowledge_fails_closed(self):
        self.brain.run_unified_cognitive_cycle(as_of_utc=AS_OF)
        with self.memory._conn:
            self.memory._conn.execute('DROP TRIGGER operational_events_no_update')
            self.memory._conn.execute("UPDATE operational_events SET payload_json='{}'")
        with self.assertRaisesRegex(ValueError, 'digest_mismatch'):
            self.brain.run_unified_cognitive_cycle(as_of_utc=AS_OF, persist=False)

    def test_recall_cannot_see_future_outcomes(self):
        self.brain.run_unified_cognitive_cycle(as_of_utc=AS_OF)
        # A separate causal preview must not see knowledge learned from later quotes.
        early_db = sqlite3.connect(':memory:')
        try:
            populate(early_db)
            early = UnifiedKatarinaBrain(early_db, self.memory).run_unified_cognitive_cycle(
                as_of_utc=START + timedelta(days=29), persist=False)
            self.assertEqual(early['knowledge_memory']['links'], ())
        finally:
            early_db.close()

    def test_invalid_mode_cannot_write_learning_or_memory(self):
        before = self.db.total_changes, self.memory._conn.total_changes
        with self.assertRaises(ValueError):
            self.brain.run_unified_cognitive_cycle(as_of_utc=AS_OF, mode='worker')
        self.assertEqual(before, (self.db.total_changes, self.memory._conn.total_changes))
