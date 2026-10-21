from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import unittest

from katarina.intelligence.cognition.owner_research_review import OwnerResearchReview, EVENT
from katarina.memory.store import MemoryStore

NOW = datetime(2026, 10, 16, 0, 0, tzinfo=timezone.utc)
SPEC = dict(hypothesis='Session breakout', entry_reason='Confirmed closed bar',
            invalidation='Structure invalid', exit_plan='Defined risk exit', source_sha256='a'*64)
EVAL = dict(result='PASS', costs='Spread, commission, slippage included in external report',
            limitations='Synthetic fixture; no real alpha proof', policy_sha256='b'*64)


class OwnerResearchReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory = MemoryStore(Path(self.tmp.name)/'memory.sqlite3')
        self.review = OwnerResearchReview(self.memory)
        self.review.register('breakout', 'v1', SPEC, now=NOW)

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def trial(self, **kwargs):
        return self.review.record_trial('breakout', 'v1', trial_id=kwargs.pop('trial_id', 'run1'),
            evidence_kind=kwargs.pop('evidence_kind', 'PROSPECTIVE_SHADOW'),
            dataset_sha256=kwargs.pop('dataset_sha256', 'c'*64),
            evaluation=kwargs.pop('evaluation', EVAL), now=kwargs.pop('now', NOW), **kwargs)

    def test_restart_retains_version_and_evidence(self):
        trial = self.trial()
        path = self.memory.path
        self.memory.close()
        self.memory = MemoryStore(path)
        self.review = OwnerResearchReview(self.memory)
        self.assertEqual(self.review.candidate('breakout', 'v1')['specification'], SPEC)
        report = self.review.weekly_report(as_of=NOW+timedelta(seconds=1))
        self.assertEqual(report['trial_count'], 1)
        self.assertEqual(report['events'][1]['review_sha256'], trial['review_sha256'])

    def test_cannot_reuse_version_for_changed_entry(self):
        with self.assertRaisesRegex(ValueError, 'version_conflict'):
            self.review.register('breakout', 'v1', {**SPEC, 'entry_reason':'Changed entry'}, now=NOW)
        self.review.register('breakout', 'v2', {**SPEC, 'entry_reason':'Changed entry'}, now=NOW)

    def test_review_bound_to_exact_trial_not_other_version(self):
        old = self.trial()
        self.review.register('breakout', 'v2', SPEC, now=NOW)
        new = self.review.record_trial('breakout', 'v2', trial_id='run2',
            evidence_kind='PROSPECTIVE_SHADOW', dataset_sha256='c'*64, evaluation=EVAL, now=NOW)
        with self.assertRaisesRegex(ValueError, 'digest_mismatch'):
            self.review.owner_review('run2', old['review_sha256'], decision='REJECT', reason='Wrong receipt', now=NOW)
        decision = self.review.owner_review('run2', new['review_sha256'],
            decision='ACCEPT_FOR_CONTROLLED_TEST_REVIEW', reason='Review exact version next', now=NOW)
        self.assertFalse(decision['strategy_activated'])
        self.assertFalse(decision['live_execution_authorized'])

    def test_synthetic_historical_failed_and_inconclusive_never_accepted(self):
        for i, (kind, result) in enumerate([('SYNTHETIC','PASS'), ('HISTORICAL','PASS'),
                ('PROSPECTIVE_SHADOW','FAIL'), ('BROKER_DEMO_FORWARD','INCONCLUSIVE')]):
            trial = self.trial(trial_id='trial'+str(i), evidence_kind=kind,
                               evaluation={**EVAL, 'result':result})
            with self.assertRaisesRegex(ValueError, 'prospective_passing'):
                self.review.owner_review(trial['trial_id'], trial['review_sha256'],
                    decision='ACCEPT_FOR_CONTROLLED_TEST_REVIEW', reason='Attempt', now=NOW)
        self.assertEqual(self.review.weekly_report(as_of=NOW+timedelta(seconds=1))['trial_count'], 4)

    def test_identical_retry_is_idempotent_conflict_refused(self):
        self.trial(); self.trial(now=NOW+timedelta(seconds=1))
        self.assertEqual(self.review.weekly_report(as_of=NOW+timedelta(seconds=2))['trial_count'], 1)
        with self.assertRaisesRegex(ValueError, 'trial_id_conflict'):
            self.trial(dataset_sha256='d'*64)

    def test_rejection_does_not_stop_research_and_failures_are_kept(self):
        trial = self.trial(evaluation={**EVAL, 'result':'FAIL'})
        self.review.owner_review('run1', trial['review_sha256'], decision='REJECT', reason='No edge', now=NOW)
        self.trial(trial_id='run2')
        report = self.review.weekly_report(as_of=NOW+timedelta(seconds=1))
        self.assertEqual(report['failed_trials'], 1)
        self.assertEqual(report['trial_count'], 2)
        self.assertEqual(report['distinct_dataset_groups'], 1)
        self.assertFalse(report['profitability_proven'])

    def test_weekly_half_open_window_and_no_mixing_evidence_types(self):
        self.trial(trial_id='old', now=NOW-timedelta(days=8))
        self.trial(trial_id='start', now=NOW-timedelta(days=7))
        self.trial(trial_id='synthetic', evidence_kind='SYNTHETIC', now=NOW-timedelta(days=1))
        self.trial(trial_id='end', now=NOW)
        report = self.review.weekly_report(as_of=NOW)
        self.assertEqual(report['trial_count'], 2)
        self.assertEqual(report['trial_counts_by_evidence_kind']['SYNTHETIC'], 1)
        self.assertEqual(report['trial_counts_by_evidence_kind']['PROSPECTIVE_SHADOW'], 1)

    def test_invalid_inputs_are_not_written(self):
        for spec in ({}, {**SPEC, 'entry_reason':''}, {**SPEC, 'source_sha256':'x'}):
            with self.assertRaises(ValueError):
                self.review.register('bad', 'v1', spec, now=NOW)
        with self.assertRaises(ValueError): self.trial(now=NOW.replace(tzinfo=None))
        with self.assertRaises(ValueError): self.trial(evaluation={**EVAL, 'policy_sha256':None})
        self.assertEqual(len(self.memory.load_recent_operational_events_of_type(EVENT)), 1)

    def test_existing_brain_owns_same_memory_and_control_scope(self):
        from katarina.intelligence.cognition.brain_runtime_control import BrainRuntimeControl
        control = BrainRuntimeControl(self.memory)
        self.assertIs(control.research_review.memory, self.memory)
        self.assertFalse(control.snapshot()['live_execution_authorized'])
        self.assertEqual(control.research_review.candidate('breakout', 'v1')['version'], 'v1')
