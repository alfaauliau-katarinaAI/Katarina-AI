"""Root-cause descriptive attribution from frozen Valetax simulation evidence.

No new model selection or order submission. Keeps distinct entry counts,
transaction costs, and held-out status separate.
"""
from collections import defaultdict, Counter
from statistics import mean, median
from math import isfinite
from pathlib import Path
import json

DIR=Path(r"C:\KatarinaDev\artifacts\historical-brain")
r=json.loads((DIR/"broker-aware-seven-symbol-study-v1.json").read_text(encoding="utf-8"))
rows=[x for x in r["trials"] if x["tp_atr"]==2 and x["sl_atr"]==1]
out=dict(report="broker_sample_root_cause",validated_edge=False,
         study_periods="Aug16-31 Sep15-30 Oct1-9 UTC exploratory",
         counts={},symbols=[],family_side=[],sessions=[])

for symbol in r["symbol_scope"]:
    a=[x for x in rows if x["symbol"]==symbol]
    b=[x for x in a if x["adverse_slippage_each_side_ticks"]==1]
    zero=[x for x in a if x["adverse_slippage_each_side_ticks"]==0]
    three=[x for x in a if x["adverse_slippage_each_side_ticks"]==3]
    index=lambda records:{(x["phase"],x["symbol"],x["family"],x["side"],x["entry_time_utc"]):x for x in records if x["status"]=="CLOSED" and x["R"] is not None}
    idx0,idx1,idx3=[index(xs) for xs in (zero,b,three)]
    keys=sorted(set(idx0)&set(idx1)&set(idx3))
    vals0=[idx0[k]["R"] for k in keys]
    vals1=[idx1[k]["R"] for k in keys]
    vals3=[idx3[k]["R"] for k in keys]
    spreads=[idx1[k]["entry_spread_div_atr"] for k in keys]
    costs=[idx1[k]["entry_spread_div_atr"]/idx1[k]["sl_atr"] for k in keys]
    stop=[idx1[k]["nominal_risk_price"] for k in keys]
    exit_types=Counter(idx1[k]["exit_reason"] for k in keys)
    entry_sig=[idx1[k] for k in keys]
    per_phase={}
    for phase in ("development_aug","development_sep","diagnostic_oct"):
        subset=[idx1[k]["R"] for k in keys if k[0]==phase]
        per_phase[phase]=dict(n=len(subset),mean_r=mean(subset) if subset else None)
    out["symbols"].append(dict(symbol=symbol,n_distinct_entry=len(keys),
       mean_r_zero_slip=mean(vals0) if vals0 else None,
       mean_r_one_tick_each=mean(vals1) if vals1 else None,
       mean_r_three_ticks_each=mean(vals3) if vals3 else None,
       mean_incremental_0_to_1_tick_r=mean(v0-v1 for v0,v1 in zip(vals0,vals1)) if vals0 else None,
       median_spread_to_ATR=median(spreads) if spreads else None,
       p90_spread_to_ATR=sorted(spreads)[int(.9*(len(spreads)-1))] if spreads else None,
       mean_entry_only_spread_in_R=mean(costs) if costs else None,
       spread_midpoint_counterfactual_caveat="Lower-bound heuristic only; TP/SL path changes if price basis changes",
       exit_types=dict(exit_types),
       results_by_phase=per_phase))
for family in ("ema20_trend_reclaim_v2","liquidity_sweep_reclaim_v2","breakout_retest_v2","impulse_break_baseline_v1"):
    for side in ("BUY","SELL"):
        subset=[x for x in rows if x["family"]==family and x["side"]==side
                  and x["adverse_slippage_each_side_ticks"]==1
                  and x["status"]=="CLOSED"]
        values=[x["R"] for x in subset]
        out["family_side"].append(dict(family=family,side=side,n=len(subset),
             mean_r=mean(values) if values else None,
             profit_factor=(sum(v for v in values if v>0)/
               (-sum(v for v in values if v<0))) if any(v<0 for v in values) else None,
             stop_fraction=sum(x["exit_reason"]=="SL" for x in subset)/len(subset) if subset else None,
             take_fraction=sum(x["exit_reason"]=="TP" for x in subset)/len(subset) if subset else None,
             mean_entry_spread_to_atr=mean(x["entry_spread_div_atr"] for x in subset) if subset else None))
out["counts"]=dict(unique_entry_scenarios=len(set((x["phase"],x["symbol"],x["family"],x["side"],x["entry_time_utc"]) for x in rows)),
                   combination_count=len(r["summaries"]),
                   scenario_rows=len(r["trials"]))
out["limits"]=["Not OOS", "Zero slippage still pays historic broker bid-ask spread",
 "No executed commission records", "Same-symbol cross-family position overlap not portfolio reconciled",
 "Profit distribution differs by stop risk and symbol", "ATR costs only on recorded qualified entries"]
target=DIR/"root-cause-broker-seven-symbols-20261010.json"
if target.exists():raise FileExistsError(str(target))
target.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps(dict(counts=out["counts"],symbols=out["symbols"],families=out["family_side"]),indent=2))
print("REPORT",target)
