"""Bounded automatic read-only routing; no execution transport or credentials stored."""
from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
import os
from pathlib import Path

METHODS = frozenset(('terminal_info', 'account_info', 'positions_get', 'orders_get',
    'symbols_get', 'symbol_info_tick', 'symbol_info', 'symbol_select',
    'copy_ticks_range', 'copy_rates_from_pos', 'copy_rates_range', 'history_deals_get'))
CONSTANTS = ('TIMEFRAME_M5', 'TIMEFRAME_M15', 'TIMEFRAME_H1', 'COPY_TICKS_INFO',
             'ACCOUNT_TRADE_MODE_DEMO')
DIAGNOSTIC_CODES = frozenset((
    'TERMINAL_UNAVAILABLE', 'TERMINAL_NOT_CONNECTED', 'TERMINAL_TRADING_MUST_BE_OFF',
    'DEMO_ACCOUNT_REQUIRED', 'ACCOUNT_UNAVAILABLE', 'ACCOUNT_LOGIN_MISMATCH', 'ACCOUNT_SERVER_MISMATCH',
    'IDENTITY_CHECK_FAILED', 'LOCAL_CONNECT_FAILED', 'LOCAL_BINDING_UNAVAILABLE',
    'LOCAL_NOT_CONNECTED', 'LOCAL_READ_FAILED', 'LOCAL_FEEDBACK_REJECTED',
    'CLOUD_NOT_CONFIGURED', 'LOCAL_MT5_PACKAGE_UNAVAILABLE',
))


def diagnostic_code(error, route):
    if isinstance(error, ImportError):
        return 'LOCAL_MT5_PACKAGE_UNAVAILABLE' if route == 'local' else 'DEPENDENCY_UNAVAILABLE'
    # Arbitrary server/exception messages can contain credentials. Only exact
    # static codes produced by our own validation may cross this boundary.
    code = str(error)
    return code if code in DIAGNOSTIC_CODES else 'CONNECTION_UNAVAILABLE'


class ConnectionUnavailable(RuntimeError):
    """Redacted connection fault; never contains server address, token or login."""


@dataclass(frozen=True)
class ConnectionConfig:
    expected_login: int
    expected_server: str
    priority: tuple[str, ...] = ('local', 'cloud')
    terminal_path: str | None = None
    cloud_url: str | None = None
    cloud_token_env: str = 'KATARINA_CLOUD_TOKEN'
    attempts: int = 2
    demo_experiments: bool = False

    def __post_init__(self):
        if type(self.demo_experiments) is not bool or (self.demo_experiments and (self.priority != ('local',) or not self.terminal_path)):
            raise ValueError('explicit_local_demo_configuration_required')
        if type(self.expected_login) is not int or self.expected_login <= 0:
            raise ValueError('expected_account_required')
        if not isinstance(self.expected_server, str) or not self.expected_server.strip():
            raise ValueError('expected_server_required')
        if (not self.priority or len(self.priority) != len(set(self.priority))
                or any(x not in ('local', 'cloud') for x in self.priority)):
            raise ValueError('invalid_connection_priority')
        if type(self.attempts) is not int or not 1 <= self.attempts <= 3:
            raise ValueError('invalid_connection_attempts')
        if self.terminal_path is not None and (not isinstance(self.terminal_path,str) or not self.terminal_path):
            raise ValueError('invalid_terminal_path')
        if not isinstance(self.cloud_token_env,str) or not self.cloud_token_env.isidentifier():
            raise ValueError('invalid_token_environment_reference')
        if self.cloud_url is not None:
            from katarina.adapters.readonly_cloud import validate_endpoint
            validate_endpoint(self.cloud_url)

    @classmethod
    def load(cls, path):
        try:
            data = json.loads(Path(path).read_text())
            if 'priority' in data:
                data['priority'] = tuple(data['priority'])
            return cls(**data)
        except (OSError, ValueError, TypeError, KeyError):
            raise ValueError('invalid_connection_config') from None


def verify_identity(broker, config):
    try:
        terminal, account = broker.terminal_info(), broker.account_info()
        flag=getattr(broker, 'ACCOUNT_TRADE_MODE_DEMO', None)
        demo_ok=(config.demo_experiments and type(flag) is int
                 and type(getattr(account,'trade_mode',None)) is int
                 and account.trade_mode == flag)
        checks = (
            (config.demo_experiments and not demo_ok, 'DEMO_ACCOUNT_REQUIRED'),
            (terminal is None, 'TERMINAL_UNAVAILABLE'),
            (getattr(terminal, 'connected', None) is not True, 'TERMINAL_NOT_CONNECTED'),
            (getattr(terminal, 'trade_allowed', None) is not False and not demo_ok, 'TERMINAL_TRADING_MUST_BE_OFF'),
            (account is None, 'ACCOUNT_UNAVAILABLE'),
            (type(getattr(account, 'login', None)) is not int
             or getattr(account, 'login', None) != config.expected_login, 'ACCOUNT_LOGIN_MISMATCH'),
            (getattr(account, 'server', None) != config.expected_server, 'ACCOUNT_SERVER_MISMATCH'),
        )
        for failed, code in checks:
            if failed:
                raise ConnectionUnavailable(code)
    except ConnectionUnavailable:
        raise
    except Exception:
        raise ConnectionUnavailable('IDENTITY_CHECK_FAILED') from None


class BoundLocalBroker:
    """Revalidate binding before every read; expose no order/login operation."""
    def __init__(self, native, config):
        self._native, self._config = native, config
        from katarina.adapters.brain_feedback import FeedbackInbox
        self._feedback = FeedbackInbox()
        self._ready = False
        self.connection_failed = False
        self._demo_service = None

    def set_demo_service(self, callback):
        if not self._config.demo_experiments or not callable(callback):
            raise ValueError('explicit_demo_service_required')
        self._demo_service=callback

    @property
    def demo_observation_enabled(self):
        return self._config.demo_experiments

    def initialize(self):
        try:
            # Only the real MetaTrader5 native module requires OS time
            # attestation; dependency-injected broker test doubles are offline.
            if getattr(self._native, "__name__", None) == "MetaTrader5":
                from katarina.intelligence.broker.host_clock_guard import require_host_clock
                require_host_clock()
            ok = (self._native.initialize(self._config.terminal_path)
                  if self._config.terminal_path else self._native.initialize())
            if not ok:
                raise ConnectionUnavailable('LOCAL_CONNECT_FAILED')
            verify_identity(self._native,self._config)
            self.connection_failed = False
            self._ready = True
            return True
        except ConnectionUnavailable:
            self.connection_failed = True
            self.shutdown()
            raise
        except Exception:
            self.connection_failed = True
            self.shutdown()
            raise ConnectionUnavailable('LOCAL_BINDING_UNAVAILABLE') from None

    def shutdown(self):
        self._ready = False
        try:
            self._native.shutdown()
        except Exception:
            pass

    def brain_feedback(self, message):
        if not self._ready:
            raise ConnectionUnavailable('LOCAL_NOT_CONNECTED')
        try:
            verify_identity(self._native, self._config)
            receipt = self._feedback.accept(message)
            verify_identity(self._native, self._config)
            return receipt
        except ConnectionUnavailable:
            self.connection_failed = True
            raise
        except Exception:
            self.connection_failed = True
            raise ConnectionUnavailable('LOCAL_FEEDBACK_REJECTED') from None

    def __getattr__(self, name):
        if name == 'COPY_TICKS_ALL':
            # Optional local capability; do not change the cloud handshake.
            return getattr(self._native,name)
        if name in CONSTANTS:
            return getattr(self._native,name)
        if name not in METHODS:
            raise AttributeError(name)
        def read(*args, **kwargs):
            if not self._ready:
                raise ConnectionUnavailable('LOCAL_NOT_CONNECTED')
            try:
                verify_identity(self._native,self._config)
                if self._demo_service is not None:
                    self._demo_service()
                    verify_identity(self._native,self._config)
                result = getattr(self._native,name)(*args,**kwargs)
                verify_identity(self._native,self._config)
                return result
            except ConnectionUnavailable:
                self.connection_failed = True
                raise
            except Exception:
                self.connection_failed = True
                raise ConnectionUnavailable('LOCAL_READ_FAILED') from None
        return read


def local_factory(config):
    return BoundLocalBroker(importlib.import_module('MetaTrader5'),config)


def cloud_factory(config):
    from katarina.adapters.readonly_cloud import CloudReadOnlyBroker
    if not config.cloud_url:
        raise ConnectionUnavailable('CLOUD_NOT_CONFIGURED')
    return CloudReadOnlyBroker(config.cloud_url,os.environ.get(config.cloud_token_env,''),config)


def run_connected(brain_type, root, *, config=None, max_symbols=17, fetch_news=True,
                  factories=None, universe=None):
    """Retry whole passes only; locks/state cleanup stay owned by the brain.

    A connection fault never resumes half a pass or replays an order. At most
    three attempts per configured route; no daemon, sleep or background worker.
    Application/data-integrity errors propagate rather than being called offline.
    """
    if universe is not None:
        from katarina.intelligence.broker.observer_universe import ObserverUniverse
        if not isinstance(universe, ObserverUniverse):
            raise ValueError('INVALID_OBSERVER_UNIVERSE')
    if config is None:
        result = brain_type.research_once(root)
        result['connection'] = {'route':'offline','reason':'ACCOUNT_BINDING_NOT_CONFIGURED',
                                'receiving_market_data':False,
                                'live_authorized':False}
        return result
    # All production routes, including cloud fallback, depend on correct
    # host UTC. Test-injected factories remain offline and deterministic.
    if factories is None:
        from katarina.intelligence.broker.host_clock_guard import require_host_clock
        require_host_clock()
    factories = factories if factories is not None else {'local':local_factory,'cloud':cloud_factory}
    faults = []
    for route in config.priority:
        for attempt in range(config.attempts):
            broker = None
            try:
                broker = factories[route](config)
                result = brain_type.observe_once(root,broker=broker,max_symbols=max_symbols,fetch_news=fetch_news,
                    **({'universe': universe} if universe is not None else {}))
                result['connection'] = {'route':route,'attempt':attempt+1,
                    'prior_faults':faults,
                    'receiving_market_data':result.get('received_market_data_symbols', 0) > 0,
                    'identity_verified':True,'live_authorized':False}
                return result
            except (ConnectionUnavailable, ImportError) as exc:
                faults.append({'route':route,'attempt':attempt+1,'reason':diagnostic_code(exc, route)})
            except RuntimeError:
                if broker is None or not getattr(broker,'connection_failed',False):
                    raise
                faults.append({'route':route,'attempt':attempt+1,'reason':'CONNECTION_LOST_DURING_PASS'})
            finally:
                if broker is not None:
                    broker.shutdown()
    result = brain_type.research_once(root)
    result['connection'] = {'route':'offline','reason':'NO_VALID_CONFIGURED_CONNECTION',
                            'receiving_market_data':False,
                            'attempts':faults,'live_authorized':False}
    return result
