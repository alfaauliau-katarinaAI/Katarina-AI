"""One foreground brain, one host lock, bounded sensor retries; LIVE OFF.

The host owns process supervision. This loop creates no worker or scheduler.
Only redacted operational counters are published; full evidence stays private.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import uuid
from contextlib import ExitStack

from katarina.adapters.automatic_connection import (
    ConnectionUnavailable, cloud_factory, local_factory, diagnostic_code,
)
from katarina.host import inspect_host
from katarina.intelligence.brain_observer import lock_worker
from katarina.intelligence.public_context import ContextStore
from katarina.intelligence.unified_brain import UnifiedKatarinaBrain
from katarina.memory.store import MemoryStore

# Identity/permission failures require investigation, never an automatic rebind.
FATAL_BINDING = frozenset(('ACCOUNT_LOGIN_MISMATCH', 'ACCOUNT_SERVER_MISMATCH',
    'TERMINAL_TRADING_MUST_BE_OFF', 'IDENTITY_CHECK_FAILED'))

# Missing market metadata is retryable; permission, identity and unknown errors stay fatal.
RECOVERABLE_SENSOR = frozenset(('BROKER_CATALOG_NOT_FOUND',
    'NO_ELIGIBLE_BROKER_SYMBOLS', 'BROKER_CLOCK_NOT_VERIFIED'))


def run_continuous(root, *, config, max_symbols=3, interval_seconds=60,
                   max_cycles=None, factories=None, brain_type=UnifiedKatarinaBrain,
                   wait=time.sleep, surface_factory=None, fetch_news=False):
    if type(fetch_news) is not bool:
        raise ValueError('invalid_news_fetch_mode')
    if config is None:
        raise ValueError('continuous_account_binding_required')
    if type(max_symbols) is not int or not 1 <= max_symbols <= 17:
        raise ValueError('max_17_broker_markets')
    if type(interval_seconds) is not int or not 30 <= interval_seconds <= 3600:
        raise ValueError('continuous_interval_30_to_3600_seconds')
    if max_cycles is not None and (type(max_cycles) is not int or max_cycles < 1):
        raise ValueError('positive_cycle_limit_required')
    root = Path(root)
    lock = lock_worker(root)
    context = memory = brain = None
    surfaces = ExitStack()
    factories = factories if factories is not None else {'local': local_factory, 'cloud': cloud_factory}
    stop = root / 'continuous.stop'
    status = dict(schema_version=1, run_id=uuid.uuid4().hex, pid=os.getpid(),
                  started_utc=datetime.now(timezone.utc).isoformat(), cycles=0,
                  successful_cycles=0, consecutive_failures=0, status='STARTING',
                  received_market_data_symbols=0, orders_submitted=0,
                  live_execution_authorized=False, production_execution=False,
                  background_workers=0, interval_seconds=interval_seconds, fetch_news=fetch_news)

    def publish(phase, reason=None):
        status.update(status=phase, reason=reason,
                      heartbeat_utc=datetime.now(timezone.utc).isoformat())
        if brain is not None:
            brain_ref = brain
            status['delivery'] = brain_ref.control.snapshot()['delivery']
            model = getattr(brain_ref, 'dashboard_model', None)
            status['model_configured'] = model is not None
            status['model_telemetry'] = model.telemetry() if callable(getattr(model,'telemetry',None)) else {}
            event_phase = 'CONNECT' if phase == 'OBSERVING' else phase
            if event_phase in ('STARTING','CONNECT','WAITING','DEGRADED','STOPPED','BLOCKED'):
                brain_ref.activity_trace.cycle = status['cycles'] + (1 if phase == 'OBSERVING' else 0)
                brain_ref.activity_trace.emit(event_phase,
                    'STARTED' if phase == 'OBSERVING' else 'IDLE' if phase == 'WAITING' else
                    'FAILED' if phase in ('DEGRADED','BLOCKED') else 'DONE')
        temp = root / 'continuous-status.tmp'
        temp.write_text(json.dumps(status, sort_keys=True) + '\n', encoding='utf-8')
        temp.replace(root / 'continuous-status.json')

    try:
        # A retained stop request cannot silently restart observation.
        if stop.exists():
            publish('STOPPED', 'EXISTING_STOP_REQUEST')
            return status
        context = ContextStore(root / 'context.sqlite3')
        memory = MemoryStore(root / 'cognitive-memory.sqlite3')
        brain = brain_type(context.db, memory)
        from katarina.monitoring.activity_trace import ActivityTrace
        brain.activity_trace = ActivityTrace(root)
        brain.context_store = context
        idle = surfaces.enter_context(surface_factory(brain)) if surface_factory else wait
        publish('STARTING')
        while not stop.exists():
            if inspect_host(root)['blockers']:
                raise RuntimeError('HOST_RESOURCE_OR_STATE_BLOCKED')
            publish('OBSERVING')
            result = None
            fault = 'NO_VALID_CONFIGURED_CONNECTION'
            for route in config.priority:
                for _ in range(config.attempts):
                    if stop.exists():
                        break
                    broker = None
                    try:
                        broker = factories[route](config)
                        result = brain.observe_connected_market(root, broker,
                            max_symbols=max_symbols, fetch_news=fetch_news)
                        break
                    except ConnectionUnavailable as exc:
                        fault = diagnostic_code(exc, route)
                        if str(exc) in FATAL_BINDING:
                            raise RuntimeError('ACCOUNT_OR_TRADING_PERMISSION_CHANGED') from None
                    except RuntimeError as exc:
                        if str(exc) not in RECOVERABLE_SENSOR:
                            raise
                        fault = str(exc)
                        brain.activity_trace.emit('SENSORS','FAILED',action=fault)
                    except ImportError:
                        # Missing packages/configuration need repair, not endless retries.
                        raise RuntimeError('SENSOR_DEPENDENCY_UNAVAILABLE') from None
                    finally:
                        if broker is not None:
                            broker.shutdown()
                if result is not None or stop.exists():
                    break
            if stop.exists():
                break
            status['cycles'] += 1
            if result is not None:
                if (result.get('orders_submitted') != 0
                        or result.get('live_execution_authorized') is not False
                        or result.get('production_execution') is not False):
                    raise RuntimeError('OBSERVATION_SAFETY_VIOLATION')
                count = result.get('received_market_data_symbols', 0)
                status['received_market_data_symbols'] = count
                if type(count) is int and count > 0:
                    status['successful_cycles'] += 1
                    status['last_success_utc'] = datetime.now(timezone.utc).isoformat()
                    status['consecutive_failures'] = 0
                    publish('WAITING')
                else:
                    fault = 'NO_USABLE_MARKET_DATA'
                    status['consecutive_failures'] += 1
                    publish('DEGRADED', fault)
            else:
                status['received_market_data_symbols'] = 0
                status['consecutive_failures'] += 1
                publish('DEGRADED', fault)
            if max_cycles is not None and status['cycles'] >= max_cycles:
                break
            # No overlapping passes or catch-up bursts. Stop latency while idle <=1s.
            delay = min(3600, interval_seconds * 2 ** min(status['consecutive_failures'], 4))
            deadline = time.monotonic() + delay
            for _ in range(delay):
                if stop.exists():
                    break
                idle(1)
                if surface_factory and time.monotonic() >= deadline:
                    break
            publish(status['status'], status['reason'])
        brain.control.checkpoint()
        publish('STOPPED', 'OWNER_STOP_REQUEST' if stop.exists() else 'CYCLE_LIMIT_REACHED')
        return status
    except KeyboardInterrupt:
        publish('STOPPED', 'INTERRUPTED')
        return status
    except Exception:
        # Never export raw exceptions containing account/server/endpoint details.
        publish('BLOCKED', 'CONTINUOUS_OBSERVATION_FAILED_CLOSED')
        raise
    finally:
        try:
            surfaces.close()
        finally:
            _close_stores(memory, context, lock)


def _close_stores(memory, context, lock):
    try:
        if memory is not None:
            memory.close()
    finally:
        try:
            if context is not None:
                context.db.close()
        finally:
            lock.close()
