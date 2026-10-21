"""Diagnose failed timed exits without selecting or changing a strategy."""
import json
from pathlib import Path
import run_zone_scalp_experiments as e

def main():
    e.ART=Path(r"C:\KatarinaDev\artifacts\mt5\zone-trace-experiments")
    e.runner.ART=e.ART
    m=json.loads((e.ROOT/"config/fast-zone-scalp-experiment-20261010.json").read_text())
    c=dict(next(c for c in m["candidates"] if c["id"]=="zone_M5_M3_M1_SELL_confirm0"))
    c["id"]+="_trace"
    r=e.execute(c,m["train_from"],m["development_to"],"diagnostic")
    out=dict(run=r,summary=e.summarize(r,m),purpose="Diagnose time-exit retcodes; no promotion")
    (e.ROOT/"docs/validation/2026-10-10-zone-time-exit-trace.json").write_text(json.dumps(out,indent=2)+"\n")

if __name__=="__main__": main()
