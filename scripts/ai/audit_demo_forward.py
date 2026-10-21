"""Read broker books and test protected candidates; NEVER sends an order."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from katarina.adapters.automatic_connection import ConnectionConfig
from katarina.intelligence.demo.demo_forward import DemoForwardRuntime


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--connection-config',required=True)
    parser.add_argument('--state-dir',required=True)
    args=parser.parse_args()
    root=Path(args.state_dir)
    status=json.loads((root/'continuous-status.json').read_text(encoding='utf-8'))
    if status.get('status')!='STOPPED' or not (root/'continuous.stop').exists():
        print('READONLY_AUDIT_REQUIRES_GRACEFULLY_STOPPED_OWNER',flush=True)
        return 2
    config=replace(ConnectionConfig.load(args.connection_config),priority=('local',),demo_experiments=True)
    runtime=DemoForwardRuntime(args.state_dir,config)
    # A retained owner stop blocks trading, not this explicitly read-only audit.
    runtime.boundary.stop_requested=lambda:False
    class AuditTrace:
        def emit(self,phase,state,**fields):
            print(json.dumps(dict(audit_phase=phase,state=state,action=fields.get('action'))),flush=True)
    runtime.trace=AuditTrace()
    print('DEMO_READONLY_AUDIT_START',flush=True)
    result=runtime.step(execute=False,force=True)
    print(json.dumps(result,allow_nan=False),flush=True)
    return 2 if result['status'] in ('DEMO_ACCOUNT_REQUIRED','DEMO_ACCOUNT_BINDING_CHANGED','DEMO_FORWARD_REQUIRES_REVIEW') else 0


if __name__=='__main__':raise SystemExit(main())
