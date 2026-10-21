import json
from statistics import median
r=json.load(open(r"C:\KatarinaDev\artifacts\historical-brain\broker-aware-seven-symbol-study-v1.json",encoding="utf-8"))
e=[x for x in r["trials"] if x["tp_atr"]==2 and x["sl_atr"]==1 and x["adverse_slippage_each_side_ticks"]==1]
for sym in ["XAUUSD.vx","EURUSD.vx","GBPUSD.vx","USDJPY.vx","NAS100.vx","US30.vx","JPN225.vx"]:
    x=[y for y in e if y["symbol"]==sym]
    v=[y["entry_ask"]-y["entry_bid"] for y in x]
    print(sym,len(x),"entry_quote_spread_median",round(median(v),8) if v else None,"median_ratio_atr",round(median(y["entry_spread_div_atr"] for y in x),4) if x else None)
