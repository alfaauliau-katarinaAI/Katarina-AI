"""One foreground brain, one host lock, bounded sensor retries; LIVE OFF.

The host owns process supervision. One optional cached-data research worker
has no broker, model, network or execution capability.
Only redacted operational counters are published; full evidence stays private.
"""
from katarina.monitoring.snapshot_io import replace_snapshot
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
from katarina.intelligence.cognition.observer import lock_worker
from katarina.intelligence.news.public_context import ContextStore
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.memory.store import MemoryStore

# Identity/permission failures require investigation, never an automatic rebind.
FATAL_BINDING = frozenset(('ACCOUNT_LOGIN_MISMATCH', 'ACCOUNT_SERVER_MISMATCH',
    'TERMINAL_TRADING_MUST_BE_OFF', 'IDENTITY_CHECK_FAILED', 'DEMO_ACCOUNT_REQUIRED'))

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
    context = memory = brain = researcher = demo = doctor = dashboard = None
    surfaces = ExitStack()
    factories = factories if factories is not None else {'local': local_factory, 'cloud': cloud_factory}
    stop = root / 'continuous.stop'
    status = dict(schema_version=1, run_id=uuid.uuid4().hex, pid=os.getpid(),
                  started_utc=datetime.now(timezone.utc).isoformat(), cycles=0,
                  successful_cycles=0, consecutive_failures=0, status='STARTING',
                  received_market_data_symbols=0, orders_submitted=0,
                  live_execution_authorized=False, production_execution=False,
                  background_workers=0, interval_seconds=interval_seconds, fetch_news=fetch_news)

    def publish(phase, reason=None, *, emit_trace=True):
        if researcher is not None:
            status['background_workers'] = researcher.background_count + int(doctor is not None and doctor.thread.is_alive())
            status['research_worker'] = dict(researcher.state)
        if doctor is not None:status['network_doctor']=dict(doctor.state)
        status.update(status=phase, reason=reason,
                      heartbeat_utc=datetime.now(timezone.utc).isoformat())
        if brain is not None:
            brain_ref = brain
            status['delivery'] = brain_ref.control.snapshot()['delivery']
            model = getattr(brain_ref, 'dashboard_model', None)
            status['model_configured'] = model is not None
            status['model_telemetry'] = model.telemetry() if callable(getattr(model,'telemetry',None)) else {}
            if researcher is not None and researcher.model is not None:
                for key in ('successful_calls','failed_calls'):
                    status['model_telemetry'][key] = status['model_telemetry'].get(key,0)+researcher.model.telemetry().get(key,0)
            event_phase = 'CONNECT' if phase == 'OBSERVING' else phase
            if emit_trace and event_phase in ('STARTING','CONNECT','WAITING','DEGRADED','STOPPED','BLOCKED'):
                brain_ref.activity_trace.cycle = status['cycles'] + (1 if phase == 'OBSERVING' else 0)
                brain_ref.activity_trace.emit(event_phase,
                    'STARTED' if phase == 'OBSERVING' else 'IDLE' if phase == 'WAITING' else
                    'FAILED' if phase in ('DEGRADED','BLOCKED') else 'DONE')
        temp = root / 'continuous-status.tmp'
        temp.write_text(json.dumps(status, sort_keys=True) + '\n', encoding='utf-8')
        replace_snapshot(temp,root / 'continuous-status.json')
        from katarina.monitoring.mt5_dashboard import publish_mt5_dashboard
        publish_mt5_dashboard(root,status,config)
        if os.environ.get('KATARINA_ALL_MARKET_RESEARCH') == '1':
            from katarina.monitoring.research_soak import record_soak
            record_soak(root, status)

    last_demo_service=-1e12
    def service_demo():
        nonlocal last_demo_service
        now=time.monotonic()
        if stop.exists():raise ConnectionUnavailable('OWNER_STOP_REQUEST')
        if demo is None or now-last_demo_service<5:return
        last_demo_service=now
        status['demo_forward']=demo.step(already_connected=True)
        publish(status['status'],status['reason'],emit_trace=False)

    def attach_demo(broker):
        setter=getattr(broker,'set_demo_service',None)
        if demo is not None and callable(setter):setter(service_demo)

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
        if os.environ.get('KATARINA_ALL_MARKET_RESEARCH') == '1':
            from katarina.intelligence.operations.parallel_storage import prepare_parallel_storage
            prepare_parallel_storage(root)
            from katarina.intelligence.lab.autonomous_research import ResearchPool
            model = getattr(brain, 'dashboard_model', None)
            if model is not None:
                from katarina.adapters.dialog_model import JSONDialogModel
                from dataclasses import replace
                model = JSONDialogModel(replace(model.config, timeout_seconds=60, max_output_tokens=min(512,model.config.max_output_tokens)))
            researcher = ResearchPool(root, brain.activity_trace, model).start()
            from katarina.intelligence.broker.data_recovery import seed_existing_gaps
            seed_existing_gaps(context.db,root,datetime.now(timezone.utc))
        if getattr(config,'demo_experiments',False) and not (root/'demo-forward'/'independent.enabled').exists():
            from katarina.intelligence.demo.demo_forward import DemoForwardRuntime
            demo=DemoForwardRuntime(root,config,trace=brain.activity_trace)
            from katarina.intelligence.operations.parallel_storage import prepare_parallel_storage
            # The private demo books also share readers with the doctor.
            from contextlib import closing
            import sqlite3
            for book in (demo.path,demo.boundary.path):
                with closing(sqlite3.connect(book,timeout=5)) as storage:
                    if storage.execute('PRAGMA journal_mode=WAL').fetchone()[0]!='wal':
                        raise RuntimeError('PARALLEL_STORAGE_UNAVAILABLE')
        if os.environ.get('KATARINA_ALL_MARKET_RESEARCH') == '1':
            from katarina.intelligence.operations.network_doctor import NetworkDoctor
            doctor=NetworkDoctor(root,brain.activity_trace,researcher,model).start()
        from katarina.monitoring.mt5_dashboard import DashboardHeartbeat
        dashboard=DashboardHeartbeat(root,config,lambda:dict(status)).start()
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
                        attach_demo(broker)
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
            close_ledger_cycle(context.db, result, fault)
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
            if demo is not None and not stop.exists():
                status["demo_forward"]=demo.step()
            # No overlapping passes or catch-up bursts. Stop latency while idle <=1s.
            delay = min(3600, interval_seconds * 2 ** min(status['consecutive_failures'], 4))
            deadline = time.monotonic() + delay
            for idle_second in range(delay):
                if stop.exists():
                    break
                idle(1)
                if (idle_second+1) % 5 == 0:
                    brain.activity_trace.emit('HEARTBEAT','IDLE')
                if (researcher is not None
                        and (idle_second+1) % 5 == 0 and not stop.exists()):
                    # Main thread alone owns broker calls and canonical SQLite writes.
                    if inspect_host(root)['blockers']:
                        raise RuntimeError('HOST_RESOURCE_OR_STATE_BLOCKED')
                    extra = None
                    try:
                        extra = factories[config.priority[0]](config)
                        attach_demo(extra)
                        if not extra.initialize():
                            raise ConnectionUnavailable('LOCAL_CONNECT_FAILED')
                        terminal = extra.terminal_info()
                        from katarina.adapters.demo_permissions import observation_permission
                        if not observation_permission(extra,terminal):
                            raise RuntimeError('ACCOUNT_OR_TRADING_PERMISSION_CHANGED')
                        from katarina.intelligence.broker.data_recovery import recover_due
                        recover_due(context.db,extra,root,datetime.now(timezone.utc),emit=brain.activity_trace.emit)
                        if (idle_second+1) % 30 == 0:
                            from katarina.intelligence.broker.auto_calibration import calibrate_due
                            calibration=calibrate_due(context.db,extra,root,datetime.now(timezone.utc),emit=brain.activity_trace.emit)
                            if calibration.get('status')!='WAIT_CALIBRATION_INTERVAL':status['calibration']=calibration
                        if (idle_second+1) % 10 == 0:
                            from katarina.intelligence.lab.continuous_research_lab import step
                            step(context.db, extra, root, datetime.now(timezone.utc), emit=brain.activity_trace.emit)
                    except ConnectionUnavailable as exc:
                        if str(exc) in FATAL_BINDING:
                            raise RuntimeError('ACCOUNT_OR_TRADING_PERMISSION_CHANGED') from None
                        brain.activity_trace.emit('HISTORY','FAILED',action='RETRY_PENDING')
                    finally:
                        if extra is not None: extra.shutdown()
                if demo is not None and (idle_second+1)%5==0 and not stop.exists():
                    status["demo_forward"]=demo.step()
                if surface_factory and time.monotonic() >= deadline:
                    break
            publish(status['status'], status['reason'])
        brain.control.checkpoint()
        publish('STOPPED', 'OWNER_STOP_REQUEST' if stop.exists() else 'CYCLE_LIMIT_REACHED')
        return status
    except KeyboardInterrupt:
        publish('STOPPED', 'INTERRUPTED')
        return status
    except Exception as exc:
        import traceback
        frame=traceback.extract_tb(exc.__traceback__)[-1]
        status['fault_diagnostic']={'type':type(exc).__name__,
            'module':Path(frame.filename).name,'line':frame.lineno}
        # Never export raw exceptions containing account/server/endpoint details.
        publish('BLOCKED', 'CONTINUOUS_OBSERVATION_FAILED_CLOSED')
        raise
    finally:
        try:
            if dashboard is not None:
                dashboard.close()
            if doctor is not None:
                doctor.close()
            if researcher is not None:
                researcher.close()
            surfaces.close()
        finally:
            _close_stores(memory, context, lock)


def close_ledger_cycle(db, result, fault):
    """Stage 0: every loop iteration ends with one ledger cycle and, on failure, its reason."""
    from katarina.intelligence.operations import observation_ledger as ledger
    finished = datetime.now(timezone.utc)
    if result is None:
        ledger.close_cycle(db, finished_utc=finished, status='FAILED', reason=fault)
        return
    state, reason = ledger.cycle_status(result)
    orders = result.get('orders_submitted')
    ledger.close_cycle(db, finished_utc=finished, cycle_id=result.get('ledger_cycle_id'),
                       status=state, reason=reason, orders_submitted=orders if type(orders) is int else 0)


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
