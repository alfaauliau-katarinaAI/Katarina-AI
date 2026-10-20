"""Technical research counters only; never neural activation or model training attestation."""
from datetime import datetime, timezone
import json
from pathlib import Path
from katarina.monitoring.runtime_details import counter, label


def summarize_learning(report):
    """Keep checkpoint time distinct from the current observation time."""
    def obj(key):
        value = report.get(key)
        return value if isinstance(value, dict) else {}
    cognition, memory, evolution = obj('unified_cognitive_cycle'), obj('neuro_link_memory'), obj('self_evolution_lab')
    def stamp(value):
        try:
            d = datetime.fromisoformat(value)
            return d.isoformat() if d.tzinfo is not None else None
        except (ValueError, TypeError):
            return None
    ledger = label(cognition.get('ledger_status'))
    matured, inserted = counter(cognition.get('matured_observations')), counter(memory.get('records_inserted'))
    counts = obj('quote_journal').get('counts', {})
    virtual = obj('virtual_shadow_summary').get('counts', {})
    return dict(
        status='NO_NEW_MATURED_EVIDENCE' if ledger == 'ALREADY_LEARNED_NO_REWRITE'
            else 'RESEARCH_REPORTED',
        source='CANONICAL_RESEARCH_SNAPSHOT',
        observation_utc=stamp(report.get('observed_at_utc')),
        cognitive_as_of_utc=stamp(cognition.get('as_of_utc')),
        ledger_status=ledger,
        matured_observations=matured, new_matured_observations=0 if ledger=='ALREADY_LEARNED_NO_REWRITE' else matured, memory_records_inserted=inserted,
        memory_records_considered=counter(memory.get('records_considered')),
        shadow_rows_read=counter(evolution.get('rows_read')),
        external_models_invoked=counter(evolution.get('external_models_invoked')),
        evolution_decision=label(evolution.get('decision')),
        no_signal_observations=counter(counts.get('NO_SIGNAL')) if isinstance(counts, dict) else None,
        virtual_open=counter(virtual.get('OPEN')) if isinstance(virtual, dict) else None,
        neural_activation_measured=False, model_training_verified=False,
        improvement_verified=False, live_authorized=False,
    )


def read_learning(root, *, observation_utc):
    """Read an existing bounded JSON snapshot; never open a database or write state."""
    unknown = dict(status='NOT_ATTESTED', source='CANONICAL_RESEARCH_SNAPSHOT')
    try:
        with (Path(root) / 'latest.json').open('rb') as stream:
            raw = stream.read(2_000_001)
        if len(raw) > 2_000_000:
            return unknown
        report = json.loads(raw)
        if not isinstance(report, dict) or report.get('observed_at_utc') != observation_utc:
            return unknown
        stamp = datetime.fromisoformat(observation_utc)
        age = (datetime.now(timezone.utc) - stamp).total_seconds()
        if not 0 <= age <= 180:
            return unknown
        return summarize_learning(report)
    except (OSError, ValueError, TypeError, UnicodeError):
        return unknown
