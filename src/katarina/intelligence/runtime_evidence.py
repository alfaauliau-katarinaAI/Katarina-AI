"""Read-only snapshot assessment. A healthy observer is never live clearance."""
from datetime import datetime, timezone
import json
from pathlib import Path


def assess_runtime(status, observation, *, now=None, max_age_seconds=180):
    if type(max_age_seconds) is not int or not 30 <= max_age_seconds <= 3600:
        raise ValueError('invalid_freshness_budget')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('aware_clock_required')
    blockers = []
    if not isinstance(status, dict) or not isinstance(observation, dict):
        status, observation = {}, {}
        blockers.append('INVALID_SNAPSHOT')

    def fresh(value):
        try:
            stamp = datetime.fromisoformat(value)
            return stamp.tzinfo is not None and 0 <= (now-stamp).total_seconds() <= max_age_seconds
        except (ValueError, TypeError):
            return False

    for label, value in [('HEARTBEAT', status.get('heartbeat_utc')),
                         ('LAST_SUCCESS', status.get('last_success_utc')),
                         ('OBSERVATION', observation.get('observed_at_utc')),
                         ('MARKET_TICK', observation.get('market_snapshot_tick_utc'))]:
        if not fresh(value):
            blockers.append(label+'_MISSING_OR_STALE')
    if status.get('status') not in ('WAITING', 'OBSERVING'):
        blockers.append('OBSERVER_NOT_HEALTHY')
    if type(status.get('consecutive_failures')) is not int or status['consecutive_failures'] != 0:
        blockers.append('OBSERVER_FAILURES_OR_MISSING_COUNTER')
    for source in (status, observation):
        if (type(source.get('orders_submitted')) is not int or source['orders_submitted'] != 0
                or source.get('live_execution_authorized') is not False
                or source.get('production_execution') is not False):
            blockers.append('LIVE_OFF_NOT_CONFIRMED')
    if type(status.get('background_workers')) is not int or status['background_workers'] != 0:
        blockers.append('UNEXPECTED_BACKGROUND_WORKERS')
    count = observation.get('received_market_data_symbols')
    observed = observation.get('observed_symbols')
    if (type(count) is not int or not 1 <= count <= 17
            or type(observed) is not int or observed != count
            or type(status.get('received_market_data_symbols')) is not int
            or status['received_market_data_symbols'] != count):
        blockers.append('MARKET_DATA_INCOMPLETE_OR_INCONSISTENT')
    feedback = observation.get('brain_hands_feedback')
    feedback = feedback if isinstance(feedback, dict) else {}
    receipts = feedback.get('receipts')
    valid = (feedback.get('status') == 'ACKNOWLEDGED_LIVE_OFF'
             and type(feedback.get('orders_submitted')) is int and feedback['orders_submitted'] == 0
             and feedback.get('broker_order_execution_verified') is False
             and isinstance(receipts, list) and type(observed) is int and len(receipts) == observed)
    seen = set()
    for receipt in receipts if isinstance(receipts, list) else []:
        if not isinstance(receipt, dict):
            valid = False
            continue
        ident, digest = receipt.get('feedback_id'), receipt.get('message_sha256')
        if (not isinstance(ident, str) or not ident or ident in seen
                or not isinstance(digest, str) or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)
                or receipt.get('status') != 'ACKNOWLEDGED_LIVE_OFF'
                or type(receipt.get('orders_submitted')) is not int or receipt['orders_submitted'] != 0
                or receipt.get('live_execution_authorized') is not False):
            valid = False
        if isinstance(ident, str):
            seen.add(ident)
    if not valid:
        blockers.append('WAIT_FEEDBACK_INCOMPLETE_OR_INVALID')
    cycles, successful = status.get('cycles'), status.get('successful_cycles')
    if (type(cycles) is not int or type(successful) is not int
            or not 1 <= successful <= cycles):
        blockers.append('INVALID_CYCLE_COUNTERS')
    from katarina.monitoring.runtime_details import runtime_details
    return dict(schema_version=1, assessed_at_utc=now.isoformat(),
                operational=runtime_details(status, observation, fresh=not blockers),
                result='BLOCKED' if blockers else 'PASS_READONLY_SNAPSHOT_ONLY',
                blockers=sorted(set(blockers)),
                received_market_data_symbols=count if type(count) is int else None,
                successful_cycles=successful if type(successful) is int else None,
                cycles=cycles if type(cycles) is int else None,
                live_clearance=False, broker_execution_verified=False,
                model_quality_verified=False, phone_tls_verified=False,
                limitations=['Snapshot counters are not independent process or source attestation',
                             'Receipt hashes are format-checked; adapter verified original message binding',
                             'Synthetic, real-model and broker execution evidence remain separate'])


def read_runtime(root, **kwargs):
    """Never opens databases, takes the brain lock, or creates host state."""
    try:
        root = Path(root)
        values = []
        for name in ('continuous-status.json', 'latest.json'):
            with (root/name).open('rb') as stream:
                payload = stream.read(2_000_001)
            if len(payload) > 2_000_000:
                raise ValueError('snapshot_too_large')
            values.append(json.loads(payload))
        return assess_runtime(*values, **kwargs)
    except (OSError, ValueError, TypeError, UnicodeError):
        result = assess_runtime({}, {}, **kwargs)
        result['blockers'].append('SNAPSHOT_UNREADABLE_OR_INVALID')
        return result
