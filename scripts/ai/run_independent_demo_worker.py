"""Run the existing protected demo execution boundary independently of scanning."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from katarina.adapters.automatic_connection import ConnectionConfig
from katarina.intelligence.demo.independent_demo_worker import run_demo_worker

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state-dir',required=True);p.add_argument('--connection-config',required=True)
    p.add_argument('--audit-only',action='store_true');p.add_argument('--max-cycles',type=int)
    a=p.parse_args()
    run_demo_worker(a.state_dir,ConnectionConfig.load(a.connection_config),audit_only=a.audit_only,max_cycles=a.max_cycles)
