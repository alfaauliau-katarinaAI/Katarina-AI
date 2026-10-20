"""Local-only MT5 dashboard transport. Display never grants execution rights."""
from katarina.monitoring.snapshot_io import replace_snapshot
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import threading

_WRITE_LOCK=threading.Lock()


def dashboard_execution(root,status,now):
    """Read E01 heartbeat separately; never renew its decision or permission age."""
    from katarina.monitoring.worker_runtime import _read, _fresh
    root=Path(root);clock=datetime.fromtimestamp(now,timezone.utc)
    executor=_read(root/'demo-forward/executor.json')
    demo=status.get('demo_forward') or {}
    pid=executor.get('pid')
    independent=(executor.get('mode')=='DEMO' and executor.get('independent') is True
                 and type(pid) is int and pid>0 and _fresh(executor,clock)
                 and executor.get('status') in ('STARTING','RUNNING','AUDIT_ONLY','RETRY_PENDING'))
    if independent:
        decision=_read(root/'demo-forward/status.json')
        demo=decision if decision.get('pid')==pid and _fresh(decision,clock) else {}
        return demo,executor.get('as_of_utc'),True
    # Once independent mode is selected, stale E01 must never fall back to a stale inline owner.
    if (root/'demo-forward/independent.enabled').exists() or executor.get('independent') is True:
        return {},None,False
    return demo,demo.get('as_of_utc'),demo.get('pid')==status.get('pid')


def publish_mt5_dashboard(root, status, config, *, target=None, now=None):
    now=time.time() if now is None else now
    if target is None:
        if os.name!='nt':return False
        base=os.environ.get('APPDATA')
        if not base:return False
        target=Path(base)/'MetaQuotes/Terminal/Common/Files/Katarina/owner-status.tsv'
    target=Path(target);root=Path(root)
    demo,executor_stamp,executor_bound=dashboard_execution(root,status,now);doctor=status.get('network_doctor') or {}
    def age(value):
        try:return max(0,int(now-datetime.fromisoformat(value).timestamp()))
        except (TypeError,ValueError):return 999999
    values=[1,int(now),status['pid'],status['status'],status.get('successful_cycles',0),
            status.get('background_workers',0),status.get('received_market_data_symbols',0),
            demo.get('execution_permission','UNKNOWN'),demo.get('status','PENDING'),
            demo.get('entry_decisions',0),demo.get('closed_outcomes',0),doctor.get('status','PENDING'),
            config.expected_login,config.expected_server,
            int((root/'continuous.stop').exists()),age(executor_stamp),
            int(executor_bound)]
    # Private local account binding only. Never published via dashboard APIs.
    raw='\t'.join(str(x).replace('\t',' ').replace('\r',' ').replace('\n',' ') for x in values)+'\n'
    try:
        target.parent.mkdir(parents=True,exist_ok=True)
        with _WRITE_LOCK:
            temp=target.with_suffix('.tmp');temp.write_text(raw,encoding='ascii');replace_snapshot(temp,target)
        return True
    except (OSError,UnicodeError):return False


class DashboardHeartbeat:
    """Actual process liveness; never refreshes market/decision timestamps."""
    def __init__(self,root,config,status,*,target=None):
        import threading
        self.root=root;self.config=config;self.status=status;self.target=target
        self.owner=threading.current_thread();self.stop=threading.Event()
        self.thread=threading.Thread(target=self.run,name='mt5-dashboard-heartbeat',daemon=True)
    def start(self):self.thread.start();return self
    def tick(self):
        status=dict(self.status())
        if not self.owner.is_alive():status['status']='BLOCKED'
        return publish_mt5_dashboard(self.root,status,self.config,target=self.target)
    def run(self):
        while not self.stop.is_set():
            try:self.tick()
            except Exception:pass # Display failure cannot interrupt the owner.
            self.stop.wait(5)
    def close(self):self.stop.set();self.thread.join(timeout=2)

