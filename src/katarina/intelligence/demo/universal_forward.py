"""Account-switch coordinator for the shared forward engine.

Research scheduling is independent. Approved strategy hashes are the only
research artifacts allowed through the execution boundary.
"""
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import time

from katarina.engines.account_authorization import account_key, AccountAuthorization
from katarina.monitoring.snapshot_io import replace_snapshot


class UniversalForwardRuntime:
    def __init__(self, root, config, *, trace=None, native=None, clock=time.time):
        import importlib
        if not config.universal_execution or config.priority != ('local',) or not config.terminal_path:
            raise ValueError('EXPLICIT_LOCAL_UNIVERSAL_CONFIGURATION_REQUIRED')
        self.root, self.config, self.trace, self.clock = Path(root), config, trace, clock
        self.native = native if native is not None else importlib.import_module('MetaTrader5')
        self.active = None
        self.key = None
        self.status = {}

    def _publish(self, status):
        self.status = dict(status, schema_version=1, pid=os.getpid(),
                           mode=self.key[0] if self.key else 'UNKNOWN')
        self.status.setdefault('as_of_utc', datetime.fromtimestamp(self.clock(), timezone.utc).isoformat())
        try:
            folder = self.root/'demo-forward'
            folder.mkdir(parents=True, exist_ok=True)
            pending = folder/'universal-status.tmp'
            pending.write_text(json.dumps(self.status, allow_nan=False)+'\n', encoding='utf-8')
            replace_snapshot(pending, folder/'status.json')
        except OSError:
            self.status['telemetry_write_failed'] = True
        return self.status

    def step(self, *, execute=True, force=False, already_connected=False):
        execution_started = False
        def paused(reason, orders_submitted=0):
            return self._publish(dict(status=reason, orders_submitted=orders_submitted,
                                      live_authorized=False, execution_permission='BLOCKED'))
        try:
            if any(p.exists() for p in (self.root/'continuous.stop', self.root/'demo-forward'/'demo.stop', self.root/'demo-forward'/'executor.stop')):
                return paused('OWNER_STOP_REQUEST')
            if not already_connected and not self.native.initialize(path=self.config.terminal_path, timeout=10000):
                return paused('TERMINAL_UNAVAILABLE')
            key = account_key(self.native, self.native.account_info())
            if key != self.key:
                self.active = None
                self.key = key
                return paused('ACCOUNT_CHANGED_REVALIDATION_REQUIRED')
            approvals = [AccountAuthorization.from_dict(a) for a in self.config.execution_authorizations]
            matches = [a for a in approvals if a.key == key and a.expires_at > self.clock()]
            if len(matches) != 1:
                self.active = None
                return paused('ACCOUNT_NOT_AUTHORIZED')
            auth = matches[0]
            if self.active is None:
                from katarina.intelligence.demo.demo_forward import DemoForwardRuntime
                # Separate ledgers, position tickets, pending submissions and losses per identity.
                folder = self.root/'accounts'/sha256(repr(key).encode()).hexdigest()
                folder.mkdir(parents=True, exist_ok=True)
                cfg = replace(self.config, expected_login=key[1], expected_server=key[2])
                self.active = DemoForwardRuntime(folder, cfg, trace=self.trace, native=self.native,
                                                 clock=self.clock, authorization=auth,
                                                 research_root=self.root)
            self.active.boundary.authorization = auth
            execution_started = True
            return self._publish(self.active.step(execute=execute, force=force, already_connected=True))
        except Exception:
            self.active = None
            return paused('ACCOUNT_VALIDATION_FAILED', None if execution_started and execute else 0)
        finally:
            if not already_connected:
                try:self.native.shutdown()
                except Exception:pass
