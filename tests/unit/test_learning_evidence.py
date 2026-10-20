"""Learning evidence must report inactivity and cached checkpoint time honestly."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from katarina.monitoring.learning_evidence import summarize_learning, read_learning


class LearningEvidenceTests(unittest.TestCase):
    def fixture(self):
        return {
            'observed_at_utc': datetime.now(timezone.utc).isoformat(),
            'unified_cognitive_cycle': {'as_of_utc': '2026-10-16T02:24:27+00:00',
                'ledger_status': 'ALREADY_LEARNED_NO_REWRITE', 'matured_observations': 0},
            'neuro_link_memory': {'records_inserted': 0, 'records_considered': 0},
            'self_evolution_lab': {'rows_read': 1, 'external_models_invoked': 0,
                'decision': 'WAIT_FOR_VERIFIED_EVIDENCE'},
            'quote_journal': {'counts': {'NO_SIGNAL': 3377}},
            'virtual_shadow_summary': {'counts': {'OPEN': 1}},
            'account_login': 'SECRET_SENTINEL',
        }

    def test_no_new_evidence_is_not_presented_as_learning(self):
        report = self.fixture()
        result = summarize_learning(report)
        self.assertEqual(result['status'], 'NO_NEW_MATURED_EVIDENCE')
        self.assertEqual(result['memory_records_inserted'], 0)
        self.assertEqual(result['shadow_rows_read'], 1)
        self.assertNotEqual(result['cognitive_as_of_utc'], result['observation_utc'])
        self.assertFalse(result['improvement_verified'])
        self.assertFalse(result['neural_activation_measured'])
        self.assertNotIn('SECRET_SENTINEL', json.dumps(result))

    def test_cumulative_matured_count_does_not_become_new_learning(self):
        report=self.fixture();report['unified_cognitive_cycle']['matured_observations']=15
        result=summarize_learning(report)
        self.assertEqual(result['status'],'NO_NEW_MATURED_EVIDENCE')
        self.assertEqual(result['matured_observations'],15)
        self.assertEqual(result['new_matured_observations'],0)

    def test_snapshot_must_match_validated_observation_and_remain_fresh(self):
        with tempfile.TemporaryDirectory() as root:
            report = self.fixture()
            path = Path(root) / 'latest.json'
            path.write_text(json.dumps(report), encoding='utf-8')
            self.assertEqual(read_learning(root, observation_utc=report['observed_at_utc'])['status'],
                             'NO_NEW_MATURED_EVIDENCE')
            self.assertEqual(read_learning(root, observation_utc='mismatch')['status'], 'NOT_ATTESTED')
            report['observed_at_utc'] = (datetime.now(timezone.utc)-timedelta(seconds=181)).isoformat()
            path.write_text(json.dumps(report), encoding='utf-8')
            self.assertEqual(read_learning(root, observation_utc=report['observed_at_utc'])['status'], 'NOT_ATTESTED')
            path.write_bytes(b'x'*2_000_001)
            self.assertEqual(read_learning(root, observation_utc=report['observed_at_utc'])['status'], 'NOT_ATTESTED')

    def test_invalid_counters_do_not_become_progress(self):
        report = self.fixture()
        report['neuro_link_memory']['records_inserted'] = True
        report['self_evolution_lab']['external_models_invoked'] = -1
        result = summarize_learning(report)
        self.assertIsNone(result['memory_records_inserted'])
        self.assertIsNone(result['external_models_invoked'])
