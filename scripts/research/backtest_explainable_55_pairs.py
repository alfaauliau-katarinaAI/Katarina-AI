"""Historical, *sampled* all-symbol replay of the actual explainable decision pipeline.

Uses only broker CLOSED M5/M15/H1 candles at each timestamp. The NEWS-VERIFIED
technical variant is counterfactual: there is NO authenticated point-in-time
historical news archive. Consequently no strategy is validated for live.

No order_send. No capital mutations. No future-bar inputs. False-positive,
WAIT and multi-symbol counts are retained; synthetic next-open fills approximate
execution, not a replacement for the MT5 tick Strategy Tester.
"""
from __future__ import annotations
import json, math, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from katarina.intelligence.cognition.market_decision_pipeline import MarketDecisionPipeline, SensorCandle
OUT=Path(r"C:\KatarinaDev\decision-backtest-20261012")
OUT.mkdir(parents=True,exist_ok=True)
SAMPLES_EVERY=36 # observed snapshots spaced by roughly 3 hours (NOT every bar)
MAX_HOLD=24      # 24 subsequent M5 bars ~ 2h
STOP_M5_ATR=1.20
TARGET_R=1.8
COST_R=.03       # extra hypothetical commission/slippage after historical spread
MIN_BARS=100
TIMEFRAME={"M5":(mt5.TIMEFRAME_M5,300,90000),"M15":(mt5.TIMEFRAME_M15,900,60000),"H1":(mt5.TIMEFRAME_H1,3600,20000)}
CUT1=1767225600
CUT2=1780272000
def date(t):return datetime.fromtimestamp(int(t),timezone.utc).isoformat()
def month(t):return date(t)[:7]
def split(t):
    if t<CUT1:return "2025_available"
    if t<CUT2:return "2026_Jan_May"
    return "2026_Jun_Oct"

def get_bars(symbol,tf,count):
    arr=None
    for request in (count, min(count,70000), min(count,45000), min(count,20000),5000):
        arr=mt5.copy_rates_from_pos(symbol,tf,1,request)
        if arr is not None and len(arr)>=MIN_BARS:break
    if arr is None or len(arr)<MIN_BARS:return None
    arr=np.sort(arr,order="time")
    # Some MT5 servers report a SINGLE stray old bar. Filter all invalid OHLC.
    check=(arr["time"]>0)&(arr["open"]>0)&(arr["high"]>=np.maximum(arr["open"],arr["close"]))&(arr["low"]<=np.minimum(arr["open"],arr["close"]))&(arr["spread"]>=0)
    arr=arr[check]
    if len(arr)<MIN_BARS:return None
    return arr
def sensors(arr,period):
    return [SensorCandle(
        datetime.fromtimestamp(int(b["time"])+period,timezone.utc),
        float(b["open"]),float(b["high"]),float(b["low"]),float(b["close"]),
        float(b["tick_volume"])) for b in arr]

def bisected_indices(t,cut,sec):
    # Available bars must be FULLY closed before (or at) decision cut.
    return int(np.searchsorted(t,cut-sec,side="right")) # exclusive index

def true_range_at(arr,i):
    if i<20:return None
    prevclose=arr["close"][i-14:i]
    highs=arr["high"][i-13:i+1]
    lows=arr["low"][i-13:i+1]
    v=np.maximum.reduce((highs-lows,abs(highs-prevclose),abs(lows-prevclose)))
    return float(v.mean())
def hypothetic_fill(bars,i,side,point,atr):
    """Entries next M5 bar open, stop-first within bar, model spread/SL gap.
    R is initial stop distance. No financing/margin/volume scaling.
    """
    if i+MAX_HOLD>=len(bars):return None
    if int(bars["time"][i+1])-int(bars["time"][i])!=300:return None
    spread=float(bars["spread"][i+1])*point
    if spread<=0 or not math.isfinite(spread):return None
    risk=max(STOP_M5_ATR*atr,4*spread,4*point)
    open_=float(bars["open"][i+1])
    entry=open_+(spread if side>0 else 0.)
    stop=entry-side*risk
    take=entry+side*risk*TARGET_R
    last=i
    for k in range(i+1,i+MAX_HOLD+1):
        if k>i+1 and int(bars["time"][k])-int(bars["time"][k-1])!=300:
            break
        bar=bars[k]
        high=float(bar["high"]);low=float(bar["low"])
        exspread=float(bar["spread"])*point
        askhi=high+exspread;asklo=low+exspread
        if side>0:
            hit_sl=low<=stop;hit_tp=high>=take
            adverse_open=min(stop,float(bar["open"]))
        else:
            hit_sl=askhi>=stop;hit_tp=asklo<=take
            adverse_open=max(stop,float(bar["open"])+exspread)
        if hit_sl:
            exprice=adverse_open
            kind="SL"
        elif hit_tp:
            exprice=take
            kind="TP"
        else:
            exprice=float(bar["close"])+(exspread if side<0 else 0.)
            kind="TIME"
        last=k
        if hit_sl or hit_tp:break
    if last==i:return None
    R=(exprice-entry)*side/risk-COST_R
    if not math.isfinite(R):return None
    return {"R":round(R,7),"exit_idx":last,"entry_time":int(bars["time"][i+1]),
            "exit_time":int(bars["time"][last])+300,"result":kind,
            "risk_price":round(risk,9)}

def stats(events):
    if not events:return {"n":0,"avg_R":None,"sum_R":0,"win_pct":None,"PF":None,"DD_R":0,"net_pct_risk025":0}
    rs=[float(e["R"]) for e in events]
    eq=0.;peak=0.;dd=0.
    for x in rs:
        eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq)
    win=sum(x>0 for x in rs)
    gain=sum(max(0.,x) for x in rs)
    loss=sum(max(0.,-x) for x in rs)
    return {"n":len(rs),"avg_R":round(sum(rs)/len(rs),5),"sum_R":round(sum(rs),4),
            "win_pct":round(win/len(rs)*100,2),
            "PF":round(gain/loss,4) if loss else None,
            "DD_R":round(dd,4),"net_pct_risk025":round(sum(rs)*.25,3)}
def analyze_symbol(symbol,n,observer,point):
    start=time.perf_counter()
    market={}
    for key,(tf,period,count) in TIMEFRAME.items():
        a=get_bars(symbol,tf,count)
        if a is None:
            return {"symbol":symbol,"status":"NO_DATA_"+key,"data":{k:len(v[0]) for k,v in market.items()}}
        market[key]=(a,sensors(a,period),period)
    b,m5,_=market["M5"]
    times={k:a["time"].astype(np.int64) for k,(a,_,_) in market.items()}
    frames=Counter();states=Counter();decisions=Counter();blocks=Counter()
    events=[];attempted=0;sampled=0;valid=0;mock_news_veto_checked=0;no_overlap=0
    invalids=Counter();end_idx=-1
    first=max(105,n%SAMPLES_EVERY+105)
    for i in range(first,len(b)-MAX_HOLD-1,SAMPLES_EVERY):
        decision_cut=int(b["time"][i])+300
        # Weekend and incomplete sessions don't magically become fresh.
        if int(b["time"][i+1])-int(b["time"][i])!=300:
            invalids["next_bar_gap"]+=1;continue
        m={}
        stale=False
        for key,(a,rows,period) in market.items():
            e=bisected_indices(times[key],decision_cut,period)
            if e<90 or e>len(rows):
                stale=True;invalids["missing_history_"+key]+=1;break
            recent_closed=int(times[key][e-1])+period
            if decision_cut-recent_closed>period*2 or recent_closed>decision_cut:
                stale=True;invalids["stale_"+key]+=1;break
            m[key]=rows[e-90:e]
        if stale:continue
        sampled+=1
        spread=float(b["spread"][i])*point
        if not math.isfinite(spread) or spread<=0:
            invalids["spread_invalid"]+=1;continue
        # Historical NEWS is NOT verified. This hypothetical test asks what the
        # technical decision would do IF that gate were known clear.
        result=observer.evaluate(symbol=symbol,candles=m,
              as_of_utc=datetime.fromtimestamp(decision_cut,timezone.utc),
              actual_spread=spread,broker_session_open=True,data_fresh=True,
              news_blackout=False,news_context_verified=True)
        detail=result.decision_detail
        valid+=1
        states[result.market_state]+=1
        decisions[result.action]+=1
        if detail is not None:
            frames[detail.activity]+=1
            for reason in detail.blockers:blocks[reason]+=1
        if result.action not in ("BUY","SELL"):continue
        attempted+=1
        if i<=end_idx:
            no_overlap+=1
            continue
        atr=true_range_at(b,i)
        if atr is None or atr<=0:
            invalids["atr_invalid"]+=1;continue
        side=1 if result.action=="BUY" else -1
        trade=hypothetic_fill(b,i,side,point,atr)
        if trade is None:
            invalids["unfilled_model"]+=1;continue
        trade.update(symbol=symbol,side=result.action,
             playbook=result.playbook,regime=result.market_state,
             research_only=True)
        events.append(trade)
        end_idx=trade["exit_idx"]
    splits={label:stats([e for e in events if split(e["entry_time"])==label])
            for label in ("2025_available","2026_Jan_May","2026_Jun_Oct")}
    all_stats=stats(events)
    return {"symbol":symbol,"status":"OK",
        "source":"MT5 closed M5/M15/H1 history, timecode as broker-provided",
        "history":{"M5":len(market["M5"][0]),"M15":len(market["M15"][0]),
                   "H1":len(market["H1"][0]),
                   "first_M5":date(b["time"][0]),"last_M5":date(b["time"][-1])},
        "samples":sampled,"observations":valid,
        "technical_attempts":attempted,"nonoverlap_filtered":no_overlap,
        "states":dict(states),"activity":dict(frames),"decisions":dict(decisions),
        "wait_blockers":dict(blocks),"quality_skips":dict(invalids),
        "trades":len(events),"overall":all_stats,"splits":splits,
        "events":events,"elapsed_sec":round(time.perf_counter()-start,1)}
def main():
    t0=time.perf_counter()
    if not mt5.initialize():raise RuntimeError("MT5 initialize failed "+repr(mt5.last_error()))
    term=mt5.terminal_info()
    if term is None or term.trade_allowed:
        mt5.shutdown()
        raise RuntimeError("Live execution risk not disabled: refuse test.")
    names=[s.name for s in mt5.symbols_get() if s.trade_mode!=mt5.SYMBOL_TRADE_MODE_DISABLED]
    print("BEGIN",len(names),"symbols","NEWS_ASSUMED_VERIFIED_FOR_TECHNICAL_DIAGNOSTIC_ONLY",
          "live=False","stride",SAMPLES_EVERY,flush=True)
    brain=MarketDecisionPipeline()
    for n,name in enumerate(names):
        out=OUT/(name.replace(".","_")+".json")
        if out.exists():
            print("SKIP_PRIOR_RESULT",n+1,name,flush=True);continue
        try:
            mt5.symbol_select(name,True)
            info=mt5.symbol_info(name)
            result=analyze_symbol(name,n,brain,float(info.point))
            out.write_text(json.dumps(result,ensure_ascii=False,indent=2,
                                      allow_nan=False),encoding="utf-8")
            x=result.get("overall",{})
            print("PAIR",n+1,"/",len(names),name,result["status"],
                  "sampled",result.get("samples",0),"signals",result.get("technical_attempts",0),
                  "trades",result.get("trades",0),"avg_R",x.get("avg_R"),
                  "secs",result.get("elapsed_sec"),flush=True)
        except Exception as exc:
            fail=dict(symbol=name,status="ERROR",error=type(exc).__name__+":"+str(exc))
            out.write_text(json.dumps(fail,indent=2),encoding="utf-8")
            print("ERROR",n+1,name,fail["error"],flush=True)
    mt5.shutdown()
    print("ALL_PAIRS_COMPLETED",len(names),"sec",round(time.perf_counter()-t0,1),
          "no_order_send",flush=True)
if __name__=="__main__":main()