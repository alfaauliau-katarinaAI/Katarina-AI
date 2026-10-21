"""Readable descriptive regime outcome report, not a trade strategy."""
import json,sys
from collections import Counter
from statistics import mean
p=sys.argv[1]
r=json.load(open(p,encoding="utf-8"))
directional={"CONTINUATION_UP","CONTINUATION_DOWN",
 "LOCAL_CONTINUATION_UP","LOCAL_CONTINUATION_DOWN",
 "REVERSAL_UP","REVERSAL_DOWN","PULLBACK_UP","PULLBACK_DOWN"}
states=Counter(x["regime"] for x in r["classified_observations"])
print("TOTAL",len(r["classified_observations"]),dict(states))
for symbol in r["distinct_instruments"]:
    group=[x for x in r["classified_observations"] if x["symbol"]==symbol]
    labels=Counter(x["regime"] for x in group)
    print("\n",symbol,"n",len(group),"states",dict(labels))
    for kind in ("CONTINUATION","LOCAL_CONTINUATION","PULLBACK","REVERSAL","SIDEWAYS","TRANSITION"):
        arr=[x for x in group if (x["regime"].startswith(kind+"_") if kind not in ("SIDEWAYS","TRANSITION") else x["regime"]==kind)]
        if not arr:continue
        for horizon in ("1h","4h"):
            v=[x["future_close_displacement"][horizon] for x in arr]
            valid=[x for x in v if x is not None]
            align=[x["aligned_with_state"] for x in valid if x["aligned_with_state"] is not None]
            print("  ",kind,horizon,"classified",len(arr),"measured",len(valid),
                  "direction_pct",round(100*mean(align),1) if align else None,
                  "mean_abs_ATR",round(mean(x["absolute_displacement_ATR"] for x in valid),3) if valid else None,
                  "mean_signed_ATR",round(mean(x["signed_directional_displacement_ATR"] for x in valid),3) if valid else None)
