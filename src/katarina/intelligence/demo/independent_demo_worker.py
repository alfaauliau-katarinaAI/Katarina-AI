"""Independent DEMO-only execution loop; no orders/MT5 permissions are bypassed."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

from katarina.monitoring.snapshot_io import replace_snapshot


class ExecutorLease:
    """OS-owned singleton lease, automatically released on crash."""
    def __init__(self, path):
        self.path=Path(path)
        self.stream=None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.stream=self.path.open('a+b')
        try:
            if sys.platform=='win32':
                import msvcrt
                self.stream.seek(0);self.stream.write(b'0');self.stream.flush();self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.stream.close();raise RuntimeError('DEMO_EXECUTOR_ALREADY_RUNNING') from None
        return self
    def __exit__(self,*_):
        self.stream.close()


def run_demo_worker(root, config, *, runtime_factory=None, wait=time.sleep,
                    interval=15, max_cycles=None, audit_only=False):
    if getattr(config,'demo_experiments',False) is not True or config.priority!=('local',):
        raise ValueError('EXPLICIT_LOCAL_DEMO_CONFIGURATION_REQUIRED')
    if not 5<=interval<=60 or type(audit_only) is not bool:
        raise ValueError('INVALID_DEMO_WORKER_OPTIONS')
    if max_cycles is not None and (type(max_cycles) is not int or max_cycles<1):
        raise ValueError('POSITIVE_CYCLE_LIMIT_REQUIRED')
    root=Path(root);private=root/'demo-forward';private.mkdir(parents=True,exist_ok=True)
    if runtime_factory is None:
        from katarina.intelligence.demo.demo_forward import DemoForwardRuntime
        runtime_factory=DemoForwardRuntime
    state=dict(schema_version=1,pid=os.getpid(),mode='DEMO',independent=True,
               audit_only=audit_only,cycles=0,live_authorized=False,status='STARTING')
    def stopped():
        return any(p.exists() for p in (root/'continuous.stop',private/'demo.stop',private/'executor.stop'))
    def publish():
        state['as_of_utc']=datetime.now(timezone.utc).isoformat()
        p=private/'executor.tmp';p.write_text(json.dumps(state)+'\n',encoding='utf-8')
        replace_snapshot(p,private/'executor.json')
    with ExecutorLease(private/'executor.lock'):
        # The runtime verifies actual broker account DEMO mode, identity, terminal
        # and account permission, portfolio risk and durable intent deduplication.
        runtime=runtime_factory(root,config)
        publish()
        while not stopped():
            try:
                result=runtime.step(execute=not audit_only)
                state['last_result']=result.get('status','UNVERIFIED')
                state['status']='AUDIT_ONLY' if audit_only else 'RUNNING'
                state.pop('error_type',None)
            except Exception as exc:
                state['status']='RETRY_PENDING'
                state['error_type']=type(exc).__name__ if type(exc).__module__=='builtins' else 'DEPENDENCY_ERROR'
            state['cycles']+=1;publish()
            if max_cycles is not None and state['cycles']>=max_cycles:break
            for _ in range(interval):
                if stopped():break
                wait(1)
        state['status']='STOPPED';publish()
    return state
