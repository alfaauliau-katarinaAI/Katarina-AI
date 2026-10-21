from collections import Counter
from statistics import mean,median
import json
p=r"C:\KatarinaDev\artifacts\historical-brain\market-regime-october-gold-nas-pilot-v1.json"
a=json.load(open(p,encoding="utf-8"))
for sym in a["distinct_instruments"]:
    events=[x for x in a["classified_observations"] if x["symbol"]==sym and x["regime"]!="UNKNOWN"]
    print(sym,"n",len(events),Counter(x["regime"] for x in events))
    for tf in ("H1","M15","M5"):
        frames=[x["frames"][tf] for x in events]
        print(tf,"direction",dict(Counter(x["direction"] for x in frames)),
         "baseline",dict(Counter(x["technical_regime_baseline"] for x in frames)),
         "median_adx",round(median(x["adx14"] for x in frames),1),
         "median_eff",round(median(x["efficiency"] for x in frames),3))
    aligned=Counter((x["frames"]["H1"]["direction"],x["frames"]["M15"]["direction"],x["frames"]["M5"]["direction"]) for x in events)
    print("alignment_top",aligned.most_common(8))
