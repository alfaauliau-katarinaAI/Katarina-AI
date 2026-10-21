"""Version-bound Owner review inside the existing brain's immutable memory.

This catalogue records research and explicit local Owner decisions, not broker
authorization. No model tool can approve a candidate. Numeric acceptance limits
remain a separately approved, pre-registered policy; this module invents none.
Caller-provided evidence remains unverified and cannot activate production code.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
import re

EVENT = 'owner_research_review_v1'
KINDS = frozenset(('SYNTHETIC', 'HISTORICAL', 'PROSPECTIVE_SHADOW', 'BROKER_DEMO_FORWARD'))


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,96}', value):
        raise ValueError('invalid_research_identifier')
    return value


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timezone_aware_time_required')
    return value.astimezone(timezone.utc)


class OwnerResearchReview:
    """A capability of BrainRuntimeControl; no worker, scheduler or delivery path.

    The caller must own the existing brain lock. Local CLI access is the trust
    boundary for Owner review until authenticated roles are implemented. This
    is not a replacement for authentication or independent evidence validation.
    """

    def __init__(self, memory):
        self.memory = memory

    def _events(self):
        rows = self.memory.load_recent_operational_events_of_type(EVENT, limit=20001)
        if len(rows) > 20000:
            raise RuntimeError('research_history_capacity_requires_archival_review')
        return rows

    def _append(self, action, payload, *, now):
        data = {'action': action, **payload, 'recorded_utc': utc(now).isoformat(),
                'orders_submitted': 0, 'live_execution_authorized': False}
        self.memory.append_operational_event(EVENT, data, created_utc=data['recorded_utc'])
        return data

    def candidate(self, method, version):
        key = (identifier(method), identifier(version))
        for row in reversed(self._events()):
            p = row['payload']
            if p['action'] == 'REGISTER' and (p['method'], p['version']) == key:
                return p
        raise ValueError('candidate_not_registered')

    def register(self, method, version, specification, *, now):
        identifier(method); identifier(version)
        if (not isinstance(specification, dict) or set(specification) != {
                'hypothesis', 'entry_reason', 'invalidation', 'exit_plan', 'source_sha256'}
                or any(not isinstance(v, str) or not v.strip() or len(v) > 4000
                       for v in specification.values())
                or not re.fullmatch(r'[0-9a-f]{64}', specification['source_sha256'])):
            raise ValueError('explicit_candidate_specification_required')
        # The version is immutable; editing any method requires a new version.
        for row in self._events():
            p = row['payload']
            if p['action'] == 'REGISTER' and (p['method'], p['version']) == (method, version):
                if p['specification_sha256'] != digest(specification):
                    raise ValueError('candidate_version_conflict')
                return p
        return self._append('REGISTER', {'method': method, 'version': version,
            'specification': specification, 'specification_sha256': digest(specification)}, now=now)

    def record_trial(self, method, version, *, trial_id, evidence_kind,
                     dataset_sha256, evaluation, now):
        candidate = self.candidate(method, version)
        identifier(trial_id)
        if (evidence_kind not in KINDS
                or not isinstance(dataset_sha256, str)
                or not re.fullmatch(r'[0-9a-f]{64}', dataset_sha256)
                or not isinstance(evaluation, dict) or set(evaluation) != {
                    'result', 'costs', 'limitations', 'policy_sha256'}
                or evaluation['result'] not in ('PASS', 'FAIL', 'INCONCLUSIVE')
                or any(not isinstance(evaluation[k], str) or not evaluation[k].strip()
                       or len(evaluation[k]) > 4000 for k in ('costs', 'limitations'))
                or not isinstance(evaluation['policy_sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', evaluation['policy_sha256'])):
            raise ValueError('invalid_research_trial')
        payload = {'method': method, 'version': version, 'trial_id': trial_id,
            'specification_sha256': candidate['specification_sha256'],
            'evidence_kind': evidence_kind, 'dataset_sha256': dataset_sha256,
            'evaluation': evaluation, 'evidence_authenticity': 'CALLER_SUPPLIED_UNVERIFIED'}
        payload['review_sha256'] = digest(payload)
        for row in self._events():
            old = row['payload']
            if old['action'] == 'TRIAL' and old['trial_id'] == trial_id:
                if old['review_sha256'] != payload['review_sha256']:
                    raise ValueError('trial_id_conflict')
                return old
        return self._append('TRIAL', payload, now=now)

    def owner_review(self, trial_id, review_sha256, *, decision, reason, now):
        """Trusted local Owner CLI only; approve controlled-test *review*, not live."""
        identifier(trial_id)
        if (decision not in ('ACCEPT_FOR_CONTROLLED_TEST_REVIEW', 'REJECT', 'DEFER')
                or not isinstance(reason, str) or not reason.strip() or len(reason) > 4000):
            raise ValueError('explicit_owner_decision_required')
        trial = next((r['payload'] for r in self._events()
                      if r['payload']['action'] == 'TRIAL'
                      and r['payload']['trial_id'] == trial_id), None)
        if trial is None or review_sha256 != trial['review_sha256']:
            raise ValueError('review_digest_mismatch')
        if decision == 'ACCEPT_FOR_CONTROLLED_TEST_REVIEW' and (
                trial['evidence_kind'] not in ('PROSPECTIVE_SHADOW', 'BROKER_DEMO_FORWARD')
                or trial['evaluation']['result'] != 'PASS'):
            raise ValueError('prospective_passing_trial_required')
        return self._append('OWNER_REVIEW', {'method': trial['method'],
            'version': trial['version'], 'trial_id': trial_id,
            'review_sha256': review_sha256, 'decision': decision, 'reason': reason,
            'authority': 'TRUSTED_LOCAL_OWNER_CLI', 'strategy_activated': False,
            'remaining_gate': 'INDEPENDENT_EVIDENCE_VALIDATION_AND_EXECUTION_CLEARANCE'}, now=now)

    def weekly_report(self, *, as_of):
        end = utc(as_of)
        start = end - timedelta(days=7)
        all_rows = self._events()
        rows = [r for r in all_rows if start <= utc(datetime.fromisoformat(
            r['payload']['recorded_utc'])) < end]
        trials = [r['payload'] for r in rows if r['payload']['action'] == 'TRIAL']
        counts = {kind: sum(p['evidence_kind'] == kind for p in trials) for kind in sorted(KINDS)}
        independent_datasets = {(p['evidence_kind'], p['dataset_sha256']) for p in trials}
        return {'report_type': 'OWNER_WEEKLY_RESEARCH_REVIEW',
            'period_start_utc': start.isoformat(), 'period_end_utc_exclusive': end.isoformat(),
            'trial_count': len(trials), 'trial_counts_by_evidence_kind': counts,
            'distinct_dataset_groups': len(independent_datasets),
            'dataset_groups_are_not_independent_alpha_proof': True,
            'failed_trials': sum(p['evaluation']['result'] == 'FAIL' for p in trials),
            'events': [r['payload'] for r in rows],
            'catalogue_candidates': [r['payload'] for r in all_rows
                                     if r['payload']['action'] == 'REGISTER'
                                     and utc(datetime.fromisoformat(r['payload']['recorded_utc'])) < end],
            'profitability_proven': False, 'strategy_activated': False,
            'orders_submitted': 0, 'live_execution_authorized': False}
