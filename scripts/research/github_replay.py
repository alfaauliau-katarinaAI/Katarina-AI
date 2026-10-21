"""KATARINA GitHub replay lab: synthetic-fixture CI and optional local private CSV replay.

No MetaTrader5 import, credentials, broker orders, or live-risk changes.
CSV: symbol,time,open,high,low,close,spread,point,volume (Unix seconds, bid OHLC).
The included fixture is SYNTHETIC; never interpret it as validated trading alpha.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

FIELDS = ("symbol","time","open","high","low","close","spread","point","volume")
METHODS = ("TREND_PULLBACK","TREND_BREAK","RANGE_FADE","RSI_REVERSAL","VOL_BREAK","LIQ_SWEEP")
CANDLES = ("NONE","BODY55","PIN")
MAX_CONFIGS_PER_PAIR = len(METHODS)*len(CANDLES)*2*2*2*3
def generate_fixture(path: Path, count=1100):
    """Deterministic, explicitly synthetic OHLC for CI correctness only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as fd:
        w=csv.DictWriter(fd,fieldnames=FIELDS);w.writeheader()
        for k,regime in enumerate(("TREND","RANGE","REVERSAL","VOLATILE")):
            rng=random.Random(1729+k); price=100.0+25*k;phase=0.;point=0.01
            for i in range(count):
                drift={"TREND":0.085,"RANGE":0,"REVERSAL":0,"VOLATILE":0}[regime]
                if regime=="REVERSAL":drift=0.17 if (i//45)%2 else -0.17
                if regime=="RANGE":drift=-0.20*(price-(100+25*k))/3
                if regime=="TREND" and (i//180)%2:drift=-0.07
                noise=rng.gauss(0,0.22 if regime!="VOLATILE" else 0.64)
                op=price;cl=max(1,op+drift+noise)
                hi=max(op,cl)+abs(rng.gauss(0,0.11))
                lo=min(op,cl)-abs(rng.gauss(0,0.11))
                spread=2+int(rng.random()*3)
                w.writerow(dict(symbol="SYN_"+regime,time=1760000000+i*900,
                    open=f"{op:.5f}",high=f"{hi:.5f}",low=f"{lo:.5f}",
                    close=f"{cl:.5f}",spread=spread,point=point,volume=80+rng.randrange(120)))
                price=cl
    return path

def read_csv(path):
    by=defaultdict(list)
    with Path(path).open(newline="",encoding="utf-8") as fd:
        reader=csv.DictReader(fd)
        needed={"symbol","time","open","high","low","close","spread","point"}
        if not needed.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV columns missing: {sorted(needed-set(reader.fieldnames or []))}")
        for row in reader:
            p={k:float(row[k]) for k in ("open","high","low","close","spread","point")}
            if not all(math.isfinite(x) for x in p.values()):
                raise ValueError("NaN/inf in chart CSV")
            if p["point"]<=0 or p["spread"]<0 or p["high"]<max(p["open"],p["close"]) or p["low"]>min(p["open"],p["close"]):
                raise ValueError("Invalid OHLC, point, or spread")
            p.update(time=int(row["time"]),symbol=row["symbol"])
            by[row["symbol"]].append(p)
    for name,rows in by.items():
        rows.sort(key=lambda x:x["time"])
        if len(set(x["time"] for x in rows))!=len(rows):
            raise ValueError(f"Duplicate timestamps {name}")
    return dict(by)

def resample(rows,minutes):
    if minutes==15:return rows
    duration=minutes*60
    out=[]
    for b in rows:
        idx=b["time"]//duration
        if not out or out[-1][0]!=idx:
            out.append([idx,dict(b)])
        else:
            z=out[-1][1]
            z["high"]=max(z["high"],b["high"]);z["low"]=min(z["low"],b["low"])
            z["close"]=b["close"];z["spread"]=b["spread"]
    # First and last groups could be incomplete. Discard both for caution.
    return [x[1] for x in out[1:-1]]

def ema(vals,n):
    out=[];prev=vals[0];a=2/(n+1)
    for v in vals:
        prev=prev+a*(v-prev);out.append(prev)
    return out
def wilder(vals,n):
    out=[];prev=vals[0]
    for v in vals:
        prev=prev+(v-prev)/n;out.append(prev)
    return out

def features(rows):
    n=len(rows)
    close=[x["close"] for x in rows];o=[x["open"] for x in rows]
    h=[x["high"] for x in rows];l=[x["low"] for x in rows]
    tr=[h[0]-l[0]]+[max(h[i]-l[i],abs(h[i]-close[i-1]),abs(l[i]-close[i-1])) for i in range(1,n)]
    atr=wilder(tr,14);e20=ema(close,20);e50=ema(close,50)
    gains=[0]+[max(0,close[i]-close[i-1]) for i in range(1,n)]
    losses=[0]+[max(0,close[i-1]-close[i]) for i in range(1,n)]
    rg=wilder(gains,14);rl=wilder(losses,14)
    rsi=[100*a/max(a+b,1e-10) for a,b in zip(rg,rl)]
    plus=[0]+[max(h[i]-h[i-1],0) if h[i]-h[i-1]>l[i-1]-l[i] else 0 for i in range(1,n)]
    minus=[0]+[max(l[i-1]-l[i],0) if l[i-1]-l[i]>h[i]-h[i-1] else 0 for i in range(1,n)]
    p=wilder(plus,14);m=wilder(minus,14)
    dx=[100*abs(a-b)/max(a+b,1e-8) for a,b in zip(p,m)]
    adx=wilder(dx,14)
    return dict(close=close,open=o,high=h,low=l,atr=atr,e20=e20,e50=e50,rsi=rsi,adx=adx)

def signal(rows,z,i,method):
    close=z["close"];atr=z["atr"];e20=z["e20"];e50=z["e50"];rsi=z["rsi"];adx=z["adx"]
    b=rows[i];c=b["close"];op=b["open"];prev=rows[i-1]
    hi20=max(z["high"][i-20:i]);lo20=min(z["low"][i-20:i])
    spread=b["spread"]*b["point"]
    if atr[i]<=max(1e-10,spread*4):return 0,"SPREAD_BLOCK"
    strength=abs(e20[i]-e50[i])/max(atr[i],1e-8)
    atrmean=sum(atr[i-40:i])/40
    vol=atr[i]>1.35*atrmean
    trend=adx[i]>=22 and strength>=0.20
    sideways=(adx[i]<=19) or (strength<0.09 and not vol)
    # Volatility takes priority, then directional trending, range, ambiguous WAIT.
    regime="VOLATILE" if vol else ("TREND" if trend else ("SIDEWAYS" if sideways else "NO_CONCLUSION"))
    if method=="TREND_PULLBACK" and regime=="TREND":
        return (1 if e20[i]>e50[i] and b["low"]<=e20[i] and c>e20[i] and c>op else -1 if e20[i]<e50[i] and b["high"]>=e20[i] and c<e20[i] and c<op else 0),regime
    if method=="TREND_BREAK" and regime=="TREND":
        return (1 if e20[i]>e50[i] and c>hi20 else -1 if e20[i]<e50[i] and c<lo20 else 0),regime
    if method=="RANGE_FADE" and regime=="SIDEWAYS":
        return (1 if b["low"]<=lo20+0.2*(hi20-lo20) and c>op else -1 if b["high"]>=hi20-0.2*(hi20-lo20) and c<op else 0),regime
    if method=="RSI_REVERSAL" and regime in ("SIDEWAYS","VOLATILE"):
        return (1 if rsi[i-1]<38<=rsi[i] and c>op else -1 if rsi[i-1]>62>=rsi[i] and c<op else 0),regime
    if method=="VOL_BREAK" and regime=="VOLATILE":
        return (1 if c>max(z["high"][i-10:i]) else -1 if c<min(z["low"][i-10:i]) else 0),regime
    if method=="LIQ_SWEEP" and regime in ("SIDEWAYS","VOLATILE"):
        return (1 if b["low"]<lo20 and c>lo20 and c>op else -1 if b["high"]>hi20 and c<hi20 and c<op else 0),regime
    return 0,regime

def candle_ok(rows,i,side,kind):
    if kind=="NONE":return True
    b=rows[i];span=max(b["high"]-b["low"],b["point"])
    body=abs(b["close"]-b["open"])/span
    if kind=="BODY55":
        return body>=.55 and (b["close"]>b["open"] if side>0 else b["close"]<b["open"])
    lw=(min(b["close"],b["open"])-b["low"])/span
    uw=(b["high"]-max(b["close"],b["open"]))/span
    return (lw>=.50 and uw<=.25) if side>0 else (uw>=.50 and lw<=.25)

def simulate_trade(rows,i,side,atr,stop_atr,rr,hold,extra_fee_r=0.05):
    """Signal at CLOSED bar i; enter next bar open; stop-first if same bar touches both."""
    if i+1>=len(rows):raise ValueError("no next bar")
    entry_bar=rows[i+1]
    spread=max(entry_bar["spread"]*entry_bar["point"],0)
    stop=max(stop_atr*atr,2.8*spread)
    entry=entry_bar["open"] + (spread if side==1 else 0)
    sl=entry-side*stop;tp=entry+side*rr*stop
    for j in range(i+1,min(len(rows),i+hold+1)):
        b=rows[j];s=b["spread"]*b["point"]
        # Stop fills can be worse after a gap. TP is filled at its level (optimistic pending liquidity).
        bidlow=b["low"];bidhigh=b["high"];asklow=bidlow+s;askhigh=bidhigh+s
        if side==1:
            stophit=bidlow<=sl;targethit=bidhigh>=tp
            exitopen=b["open"]
        else:
            stophit=askhigh>=sl;targethit=asklow<=tp
            exitopen=b["open"]+s
        if stophit:
            exit_price=min(sl,exitopen) if side==1 else max(sl,exitopen)
            return (side*(exit_price-entry)/stop-extra_fee_r,j,"STOP")
        if targethit:return (rr-extra_fee_r,j,"TARGET")
    j=min(len(rows)-1,i+hold)
    b=rows[j];exit_price=b["close"] + (b["spread"]*b["point"] if side==-1 else 0)
    return (side*(exit_price-entry)/stop-extra_fee_r,j,"TIME_EXIT")

def replay(rows,method,candle,stop,rr,hold,extra=.05):
    z=features(rows);events=[];i=70
    while i+1<len(rows):
        side,regime=signal(rows,z,i,method)
        if side and candle_ok(rows,i,side,candle):
            r,j,why=simulate_trade(rows,i,side,z["atr"][i],stop,rr,hold,extra)
            events.append(dict(time=rows[i+1]["time"],exit=rows[j]["time"],side=side,R=round(r,7),regime=regime,exit_reason=why))
            i=max(i+1,j+1)
        else:i+=1
    return events

def measure(events):
    rv=[x["R"] for x in events]
    if not rv:return dict(n=0,meanR=0.0,pf=0.,maxDD_R=0.,winRate=0.)
    equity=0.;peak=0.;dd=0.
    for v in rv:equity+=v;peak=max(peak,equity);dd=max(dd,peak-equity)
    pos=sum(max(0,x) for x in rv);neg=sum(max(0,-x) for x in rv)
    return dict(n=len(rv),meanR=round(sum(rv)/len(rv),5),pf=round(pos/neg,4) if neg else None,maxDD_R=round(dd,4),winRate=round(sum(x>0 for x in rv)/len(rv),4))

def evaluation(dataset, min_trades=5):
    report=dict(kind="KATARINA_GITHUB_REPLAY",research_only=True,live_execution_authorized=False,
       dataset_type="synthetic" if all(k.startswith("SYN_") for k in dataset) else "broker_or_external_csv",
       selection_rule="train first 60% only; never tune on validation or last 20%",
       warnings=["Synthetic prices never prove profitable real-world performance",
          "Historical splits from previously viewed dates are not independent unseen OOS",
          "OHLC not true tick; no real broker fills, margin, swap, dynamic latency, or news",
          "No configs are authorized for live trading"],pairs=[],configurations_evaluated=0)
    for symbol,bars in sorted(dataset.items()):
        for tf in (15,30,60):
            rows=resample(bars,tf)
            if len(rows)<240:continue
            train_end=int(len(rows)*.6);val_end=int(len(rows)*.8)
            # Build train/validation/test separately so no trade crosses split boundary.
            train,val,holdout=rows[:train_end],rows[train_end:val_end],rows[val_end:]
            # No overlap: signals start after 70 closed bars for each partition.
            winner=None;best_score=-1e9
            for method in METHODS:
                for candle in CANDLES:
                    for stop in (.8,1.2):
                        for rr in (1.5,2.5):
                            for hold in (8,16):
                                report["configurations_evaluated"]+=1
                                ev=replay(train,method,candle,stop,rr,hold)
                                m=measure(ev)
                                if m["n"]<min_trades:continue
                                score=m["meanR"]-0.018*m["maxDD_R"]-.2/math.sqrt(m["n"])
                                if score>best_score:
                                    best_score=score;winner=(method,candle,stop,rr,hold,m)
            if winner is None:
                report["pairs"].append(dict(symbol=symbol,timeframe=f"M{tf}",status="NO_TRAIN_CANDIDATE",train_bars=len(train),validation_bars=len(val),test_bars=len(holdout)));continue
            method,candle,stop,rr,hold,m=winner
            va=measure(replay(val,method,candle,stop,rr,hold))
            ts=measure(replay(holdout,method,candle,stop,rr,hold))
            # Add extra 0.10R stress on *every* filled trade.
            vs=measure(replay(val,method,candle,stop,rr,hold,extra=.15))
            hs=measure(replay(holdout,method,candle,stop,rr,hold,extra=.15))
            status="RESEARCH_ONLY_NEEDS_UNSEEN_DATA"
            if va["n"]<min_trades or ts["n"]<min_trades or vs["meanR"]<=0 or hs["meanR"]<=0:
                status="REJECT_UNSTABLE_OR_TOO_FEW_EVENTS"
            report["pairs"].append(dict(symbol=symbol,timeframe=f"M{tf}",family=method,candle=candle,
                stop_atr=stop,rr=rr,hold_bars=hold,train=m,validation=va,diagnostic=ts,
                stress_validation=vs,stress_diagnostic=hs,status=status))
    report["counts"]=dict(symbols=len(dataset),timeframe_attempts=len(report["pairs"]),
        research_only=sum(x.get("status")=="RESEARCH_ONLY_NEEDS_UNSEEN_DATA" for x in report["pairs"]),
        rejected=sum(x.get("status")!="RESEARCH_ONLY_NEEDS_UNSEEN_DATA" for x in report["pairs"]))
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",help="CSV input, required unless using --generate-synthetic")
    parser.add_argument("--generate-synthetic",help="Write deterministic CI fixture CSV")
    parser.add_argument("--output",default="build/replay/replay-report.json")
    parser.add_argument("--min-trades",type=int,default=5)
    args=parser.parse_args()
    if args.generate_synthetic:
        generate_fixture(Path(args.generate_synthetic))
        if not args.input: args.input=args.generate_synthetic
    if not args.input:parser.error("Specify --input or --generate-synthetic")
    if not (1<=args.min_trades<=10000):parser.error("--min-trades must be 1..10000")
    data=read_csv(args.input);result=evaluation(data,args.min_trades)
    outfile=Path(args.output);outfile.parent.mkdir(parents=True,exist_ok=True)
    outfile.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("KATARINA_REPLAY",json.dumps(dict(counts=result["counts"],grid=result["configurations_evaluated"],
        dataset=result["dataset_type"],live_authorized=result["live_execution_authorized"])))
if __name__=="__main__":main()