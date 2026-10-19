"""Send the allowlisted VPS test snapshot to the stable monitor URL."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from katarina.monitoring.monitor_publisher import run

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--state-dir',required=True)
    p.add_argument('--config',required=True)
    p.add_argument('--interval-seconds',type=int,default=15)
    p.add_argument('--once',action='store_true')
    a=p.parse_args()
    return 0 if run(a.state_dir,a.config,interval_seconds=a.interval_seconds,once=a.once)['status']=='PUBLISHED' else 2

if __name__=='__main__':
    raise SystemExit(main())
