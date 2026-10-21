"""Read-only scheduled shadow lookup against validated historical memory.

Never sends orders, never writes to model permissions. New snapshots must
be later than memory freeze and not stale/UNKNOWN. Persist only metadata
and historical examples, never as a trade signal.
"""
from __future__ import annotations
import argparse,json,os
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from katarina.intelligence.perception.historical_analog_memory import (
    query_analogs,load_frozen_symbol_memory)

UTC=timezone.utc
REGIMES=("CONTINUATION_UP","CONTINUATION_DOWN","LOCAL_CONTINUATION_UP",
    "LOCAL_CONTINUATION_DOWN","PULLBACK_UP","PULLBACK_DOWN",
    "REVERSAL_UP","REVERSAL_DOWN","SIDEWAYS","TRANSITION")
MAX_OBSERVATION_AGE_SECONDS=600.

def time(s):
    d=datetime.fromisoformat(s)
    if d.tzinfo is None:raise ValueError("timestamp_without_timezone")
    return d.timestamp()

def evaluate_observer(frozen,latest,now):
    ts=now.timestamp()
    results=[]
    for row in latest.get("symbols",[]):
        name=row.get("symbol")
        if name not in frozen["by_symbol"]:continue
        raw=row.get("market_regime_v1") or {}
        state=raw.get("regime")
        checked=dict(symbol=name,regime=state or "UNKNOWN",
            read_only=True,trading_permission=False,
            horizons={},latest_snapshot_utc=raw.get("observed_utc"))
        if (state not in REGIMES or raw.get("entry_authorized") is not False or
            not raw.get("observed_utc") or
            set(raw.get("frames",{}))!={"M5","M15","H1"}):
            checked["status"]="ABSTAIN_INVALID_OR_MISSING_REGIME"
            results.append(checked);continue
        current=time(raw["observed_utc"])
        if not 0<=ts-current<=MAX_OBSERVATION_AGE_SECONDS:
            checked["status"]="ABSTAIN_STALE_REGIME"
            results.append(checked);continue
        if current<=time(frozen["asof_utc"]):
            checked["status"]="ABSTAIN_DATA_WITHIN_HISTORICAL_TRAINING"
            results.append(checked);continue
        source=dict(symbol=name,regime=state,
            frames=raw["frames"],close_time_utc=raw["observed_utc"])
        for horizon in (1,4):
            bank=load_frozen_symbol_memory(frozen,name,horizon,current)
            estimated=query_analogs(bank,source,current)
            checked["horizons"][str(horizon)+"h"]=estimated
        checked["status"]="RESEARCH_HISTORY_COMPARISON_ONLY"
        results.append(checked)
    return dict(kind="KATARINA_current_historical_analogs_shadow_v1",
         as_of_utc=now.isoformat(),
         observer_snapshot_utc=latest.get("as_of_utc"),
         connected_symbol_profiles=len(results),
         decision="NO_TRADE",
         quantitative_historical_examples_not_real_execution=True,
         no_calibrated_profit_probability=True,
         no_auto_trades_or_order_send=True,
         live_execution_enabled=False,model_promotion_allowed=False,
         by_symbol=results)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--memory",required=True)
    p.add_argument("--observer",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    raw=Path(a.memory).read_bytes()
    memory=json.loads(raw)
    if memory.get("kind")!="frozen_per_symbol_historical_analog_memory_v1":
        raise ValueError("wrong_memory_source")
    observer=Path(a.observer).read_bytes()
    latest=json.loads(observer)
    if latest.get("decision")!="NO_TRADE" or latest.get("live_execution_enabled") is not False:
        raise ValueError("observer_trading_permission_forbidden")
    doc=evaluate_observer(memory,latest,datetime.now(UTC))
    doc["provenance_sha256"]=dict(frozen=sha256(raw).hexdigest(),
        observer=sha256(observer).hexdigest())
    out=Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    os.replace(str(tmp),str(out))
    print("asof",doc["as_of_utc"],"symbols",doc["connected_symbol_profiles"],
          "status",[(r["symbol"],r["status"]) for r in doc["by_symbol"]],
          "NO_TRADE",flush=True)
if __name__=="__main__":
    main()
