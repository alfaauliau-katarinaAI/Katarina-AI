"""Portable read-only UTC synchronization preflight; never starts MT5 or trades.

    python scripts/ai/check_host_clock.py
Returns 0 when the host OS reports recently synchronized time, else 2.
This cannot replace checking an independent UTC reference during migration.
"""
from pathlib import Path
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from katarina.intelligence.broker.host_clock_guard import inspect_host_clock


def main():
    result=inspect_host_clock()
    print(json.dumps({"status":"READY" if result.synchronized else "BLOCKED",
                      "clock_source":result.source, "reason":result.reason,
                      "canonical_time":"UTC", "live_authorized":False},sort_keys=True))
    return 0 if result.synchronized else 2


if __name__=="__main__":
    raise SystemExit(main())
