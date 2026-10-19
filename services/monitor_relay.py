"""Run only the technical dashboard relay on the free web host."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from katarina.monitoring.monitor_relay import serve

if __name__=='__main__':
    serve()
