"""Inspect point-in-time opening-session coverage for index CFD, no order."""
from datetime import datetime,timezone
from collections import Counter
import MetaTrader5 as mt5,json
p=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe"
assert mt5.initialize(p,timeout=20000)
out={}
try:
    for symbol in ("JPN225.vx","US30.vx","NAS100.vx"):
        a=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,
            datetime(2026,9,21,tzinfo=timezone.utc),
            datetime(2026,9,26,tzinfo=timezone.utc))
        b=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M5,
            datetime(2026,9,21,tzinfo=timezone.utc),
            datetime(2026,9,26,tzinfo=timezone.utc))
        tim=[int(x["time"]) for x in a] if a is not None else []
        if not tim:
            out[symbol]=dict(m1bars=0,m5bars=0);continue
        by_hour=Counter(datetime.fromtimestamp(t,timezone.utc).hour for t in tim)
        t_on_open=[t for t in tim if 0<=datetime.fromtimestamp(t,timezone.utc).hour<3]
        # Longest contiguous M1 run ending near Tokyo 09:30 JST,
        # independently of 120 M1 bars prehistory used in old scanner.
        streaks={}
        for t in t_on_open:
            hr=datetime.fromtimestamp(t,timezone.utc).strftime("%Y-%m-%dT%H:%M")
            if t%86400>=30*60 and t%86400<180*60 and t%60==0:
                prior=[tt for tt in tim if tt<=t and tt>=t-140*60]
                tail=1
                for x,y in zip(prior[:-1],prior[1:]):
                    if y==x+60:tail+=1
                    else:tail=1
                if t%86400==35*60:
                    streaks[datetime.fromtimestamp(t,timezone.utc).strftime("%Y-%m-%d")]=tail
        out[symbol]=dict(m1bars=len(tim),m5bars=None if b is None else len(b),
           sample_days=sorted(set(datetime.fromtimestamp(t,timezone.utc).strftime("%Y-%m-%d") for t in tim)),
           count_M1_UTC_0_1_2={str(h):by_hour[h] for h in (0,1,2)},
           first_M1_UTC_hours={str(h):next((datetime.fromtimestamp(t,timezone.utc).strftime("%Y-%m-%dT%H:%M") for t in tim if datetime.fromtimestamp(t,timezone.utc).hour==h),None) for h in (0,1,2)},
           consecutive_M1_bars_at_0035=streaks)
finally:mt5.shutdown()
print(json.dumps(out,indent=2))
