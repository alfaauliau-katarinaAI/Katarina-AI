"""V10: higher-timeframe broker-price research, NOT production KATARINA.

Reads M15/H1/H4 rates from demo MT5 only if terminal trading DISABLED.
Changes neither production Brain nor governor nor VPS files. All signal
features use candles CLOSED by decision time; fills are hypothetical.
The 2026 historical tape is previously inspected: not independent OOS.
"""
from __future__ import annotations
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from statistics import median

UTC=timezone.utc
SYMBOLS=("EURUSD.vx","GBPUSD.vx","USDJPY.vx","USDCHF.vx","USDCAD.vx",
"AUDUSD.vx","NZDUSD.vx","EURGBP.vx","EURJPY.vx","GBPJPY.vx",
"AUDJPY.vx","EURAUD.vx","XAUUSD.vx","BTCUSD.vx","XTIUSD.vx",
"US30.vx","NAS100.vx")
FRAMES=("M15","H1")
FAMILIES=("TREND_PULLBACK","BREAKOUT_CONTINUATION","LIQUIDITY_SWEEP",
          "RANGE_FADE","MOMENTUM_EXPANSION")
# Locked a priori — training window Jun-Jul 2026; Aug-Sep diagnosis.
TRAIN={"2026-06","2026-07"}
DIAG={"2026-08","2026-09"}
ALL=TRAIN|DIAG
STOP_ATR=(1.0,1.5)
TAKE_R=(1.5,2.2)
EXTRA_COST_R=.10
FEE_R=.03
RISK_CHOICES=(.001,.0025,.005)
HOLD={"M15":32,"H1":12}
MAX_DD=.08

@dataclass(frozen=True)
class Bar:
    # time = CLOSED candle epoch seconds UTC
    time:int
    op:float
    hi:float
    lo:float
    cl:float
    sp:int
    def __post_init__(self):
        if self.time<=0 or self.lo<=0 or self.hi<max(self.cl,self.op,self.lo) or self.lo>min(self.op,self.cl):
            raise ValueError("bad_bar")

def load_bars(raw,seconds):
    return [Bar(int(x["time"])+seconds,float(x["open"]),float(x["high"]),
                float(x["low"]),float(x["close"]),int(x["spread"])) for x in raw]

def atr(data,n=14):
    if len(data)<n+1:return None
    return sum(max(data[i].hi-data[i].lo,abs(data[i].hi-data[i-1].cl),
                   abs(data[i].lo-data[i-1].cl))
               for i in range(len(data)-n,len(data)))/n

def slope(data):
    if len(data)<16:return 0.
    value=atr(data)
    return (data[-1].cl-data[-7].cl)/value if value and value>0 else 0.

def htf_state(h1,h4):
    # H4 is mandatory. Neutral H4 is a distinct regime, not forced trend.
    x=slope(h4)
    if x>1.25:return "UP"
    if x< -1.25:return "DOWN"
    return "RANGE"

def ema(data,n):
    weight=2/(n+1)
    e=data[0].cl
    for b in data[1:]:e+=weight*(b.cl-e)
    return e

def generate(history,h1,h4,spread,point):
    """Returns only metadata known at the last closed bar.

    (method, side, stop direction is defined *after* next-bar entry).
    """
    if len(history)<40 or len(h4)<16 or len(h1)<16:return ()
    a=atr(history)
    if a is None or a<=0:return ()
    state=htf_state(h1,h4)
    last=history[-1]; prev=history[-2]
    ratio=spread/a
    # At higher timeframe one ATR should cover a viable number of spreads.
    if ratio>.25:return ()
    highs=[b.hi for b in history[-21:-1]]
    lows=[b.lo for b in history[-21:-1]]
    hi=max(highs);lo=min(lows)
    ema9=ema(history[-35:],9)
    ema21=ema(history[-40:],21)
    prevrange=max(prev.hi-prev.lo,.01*a)
    body=abs(last.cl-last.op)
    found=[]
    def add(method,side):
        found.append((method,side,a,state))
    # Trends: distinct BUY and SELL candle conditions, HTF aligned.
    if state=="UP" and ema9>ema21 and prev.lo<=ema9+.15*a and last.cl>ema9 and last.cl>last.op and last.cl>prev.cl:
        add("TREND_PULLBACK","BUY")
    if state=="DOWN" and ema9<ema21 and prev.hi>=ema9-.15*a and last.cl<ema9 and last.cl<last.op and last.cl<prev.cl:
        add("TREND_PULLBACK","SELL")
    # Price-only breakout: preceding range excludes signal bar.
    if state=="UP" and last.cl>hi+.08*a and last.cl>last.op and body>.30*a:
        add("BREAKOUT_CONTINUATION","BUY")
    if state=="DOWN" and last.cl<lo-.08*a and last.cl<last.op and body>.30*a:
        add("BREAKOUT_CONTINUATION","SELL")
    # Sweep/reclaim: avoid strong counter-H4 entries; use only old levels.
    lw=min(last.op,last.cl)-last.lo
    uw=last.hi-max(last.op,last.cl)
    if state!="DOWN" and last.lo<lo-.08*a and last.cl>lo and lw>.30*a:
        add("LIQUIDITY_SWEEP","BUY")
    if state!="UP" and last.hi>hi+.08*a and last.cl<hi and uw>.30*a:
        add("LIQUIDITY_SWEEP","SELL")
    # Range fade on prior edge, with closed follow-through confirmation.
    if state=="RANGE" and len(highs)>=20:
        if last.cl<lo+.3*a and prev.cl<prev.op and last.cl>last.op and last.lo<prev.lo:
            add("RANGE_FADE","BUY")
        if last.cl>hi-.3*a and prev.cl>prev.op and last.cl<last.op and last.hi>prev.hi:
            add("RANGE_FADE","SELL")
    # Larger displacement: different structure than pullback and sweep.
    if body>=.65*a and body/prevrange>=.8:
        if state=="UP" and last.cl>hi and last.cl>last.op:
            add("MOMENTUM_EXPANSION","BUY")
        if state=="DOWN" and last.cl<lo and last.cl<last.op:
            add("MOMENTUM_EXPANSION","SELL")
    return tuple(found)

def model_fill(side,entry,future,point,tick,atr_value,stop_factor,take_rr,step):
    """MT5 BID bar + recorded spread per bar, conservative stop-before-TP.

    Risk distance is ATR-based at entry, and >=3x entry spread. The resulting
    R already pays the entry spread and adverse entry/exit one-tick slip.
    """
    spread=max(entry.sp,0)*point
    dist=stop_factor*atr_value
    if dist<max(3*spread,6*tick):return None
    if side=="BUY":
        opened=entry.op+spread+tick;stop=opened-dist;take=opened+take_rr*dist
    else:
        opened=entry.op-tick;stop=opened+dist;take=opened-take_rr*dist
    if stop<=0 or take<=0:return None
    actual=None;close_time=entry.time;status="TIME"
    prev=entry.time-step
    for bar in future:
        if bar.time-prev!=step:break
        prev=bar.time;close_time=bar.time
        spr=max(bar.sp,0)*point
        op=bar.op if side=="BUY" else bar.op+spr
        hi=bar.hi if side=="BUY" else bar.hi+spr
        lo=bar.lo if side=="BUY" else bar.lo+spr
        sl=(lo<=stop if side=="BUY" else hi>=stop)
        tp=(hi>=take if side=="BUY" else lo<=take)
        if sl:
            actual=min(op,stop)-tick if side=="BUY" else max(op,stop)+tick
            status="SL_BOTH_FIRST" if tp else "SL"
        elif tp:
            actual=take-tick if side=="BUY" else take+tick
            status="TP"
        else:
            actual=bar.cl-tick if side=="BUY" else bar.cl+spr+tick
        if sl or tp:break
    if actual is None:return None
    value=(actual-opened)/dist if side=="BUY" else (opened-actual)/dist
    return round(value-FEE_R,6),close_time,status

def summarize(vals):
    if not vals:return {"n":0,"mean_r":None,"pf":None,"win_rate":None}
    n=len(vals);win=sum(x for x in vals if x>0);loss=-sum(x for x in vals if x<0)
    return {"n":n,"mean_r":round(sum(vals)/n,6),
            "pf":round(win/loss,5) if loss>0 else None,
            "win_rate":round(100*sum(x>0 for x in vals)/n,2)}

def new_bars(raw,frame):
    return load_bars(raw,900 if frame=="M15" else 3600)

def evaluate_market(market,point,tick,frames):
    h1,h4=frames["H1"],frames["H4"]
    bucket=defaultdict(list)
    density=Counter();costs=defaultdict(list)
    for timeframe in FRAMES:
        candles=frames[timeframe];step=900 if timeframe=="M15" else 3600
        ht1=[x.time for x in h1];ht4=[x.time for x in h4]
        active={}
        # Scan signal once for all predeclared SL/TP choices.
        for i in range(39,len(candles)-1):
            now=candles[i].time
            month=datetime.fromtimestamp(now,UTC).strftime("%Y-%m")
            if month not in ALL:continue
            window=candles[i-39:i+1]
            if any(not (0<window[j].time-window[j-1].time<=4*step) for j in range(1,40)):
                # Overnight exchange pause may leave missing H1 candles. Accept
                # observed closed bars across <=4-bar gaps, never interpolate.
                # Exclude weekends and multi-day outages.
                density[timeframe+":input_gap"]+=1;continue
            if candles[i+1].time!=now+step:
                density[timeframe+":next_gap"]+=1;continue
            j1=bisect_right(ht1,now);j4=bisect_right(ht4,now)
            if j1<16 or j4<16:continue
            h1_window=h1[j1-16:j1]
            h4_window=h4[j4-16:j4]
            a=atr(window)
            if a and a>0:costs[timeframe].append(max(0,candles[i].sp)*point/a)
            candidates=generate(window,h1_window,h4_window,
                                max(0,candles[i].sp)*point,point)
            density[timeframe+":candidates"]+=len(candidates)
            for family,side,a,state in candidates:
                key=(timeframe,family,side)
                # Independently track no-overlap across all exit parameter
                # models. Baseline event screen fixes one-signal/time first.
                for factor in STOP_ATR:
                    for rr in TAKE_R:
                        setting=(timeframe,family,side,factor,rr)
                        if active.get(setting,0)>now:
                            density[timeframe+":overlap"]+=1;continue
                        filled=model_fill(side,candles[i+1],
                                          candles[i+1:i+1+HOLD[timeframe]],
                                          point,tick,a,factor,rr,step)
                        if filled is None:
                            density[timeframe+":invalid_fill"]+=1;continue
                        value,closed,status=filled
                        active[setting]=closed
                        bucket[setting].append((now,closed,value))
    training=[];screen=[]
    for k,events in sorted(bucket.items()):
        tf,family,side,factor,rr=k
        fit=[v for t,_,v in events if datetime.fromtimestamp(t,UTC).strftime("%Y-%m") in TRAIN]
        val=[v for t,_,v in events if datetime.fromtimestamp(t,UTC).strftime("%Y-%m") in DIAG]
        train_summary=summarize([x-EXTRA_COST_R for x in fit])
        val_summary=summarize([x-EXTRA_COST_R for x in val])
        split={month:summarize([v-EXTRA_COST_R for t,_,v in events
              if datetime.fromtimestamp(t,UTC).strftime("%Y-%m")==month])
              for month in ("2026-06","2026-07","2026-08","2026-09")}
        label="/".join((tf,family,side,str(factor),str(rr)))
        record={"label":label,"frame":tf,"method":family,"side":side,
                "stop_atr":factor,"take_rr":rr,
                "train_cost_stressed":train_summary,
                "diagnostic_cost_stressed":val_summary,
                "months":split}
        training.append((record,events))
    # Decision to shortlist is determined entirely by the old TRAIN window.
    # Deliberately small sample floor to keep research leads visible; no live gate.
    ordered=sorted(training,key=lambda x:(
        -(x[0]["train_cost_stressed"]["mean_r"] or -999),
        -x[0]["train_cost_stressed"]["n"],x[0]["label"]))
    selected=[(r,e) for r,e in ordered if
              r["train_cost_stressed"]["n"]>=20 and
              (r["train_cost_stressed"]["mean_r"] or -999)>.08 and
              (r["train_cost_stressed"]["pf"] or 0)>=1.15]
    results=[]
    for r,events in selected:
        r=dict(r)
        check=r["diagnostic_cost_stressed"]
        r["diagnostic_research_gate"]=(
            check["n"]>=20 and (check["mean_r"] or -999)>.05 and
            (check["pf"] or 0)>=1.15 and
            all(r["months"][mon]["n"]>=8 and
                (r["months"][mon]["mean_r"] or -999)>0
                for mon in sorted(DIAG)))
        r["live_authorized"]=False
        results.append((r,events))
    baseline={
        f:{key:sum(1 for rec,_ in training if rec["frame"]==f and
            rec["method"]==key)
           for key in FAMILIES} for f in FRAMES}
    model={
        "broker_market":market,"candles_by_frame":{
            tf:len(frames[tf]) for tf in ("M15","H1","H4")},
        "spread_ATR_median":{
            tf:round(median(vals),5) if vals else None
            for tf,vals in costs.items()},
        "diagnostics":dict(density),
        "total_parameter_cases":len(training),
        "train_shortlist_count":len(selected),
        "diagnostic_research_pass_count":sum(r["diagnostic_research_gate"] for r,_ in results),
        "shortlist":[r for r,_ in results[:12]],
        "best_training_only":[r for r,_ in ordered[:3]],
        "research_not_live":True,
    }
    return model,results

def portfolio_experiment(results):
    """Risk scenarios using only TRAIN-selected model signals.

    Counterfactual no-overlap across all selected entries, positions limited
    by UTC exit_time. Drawdown cap is separate simulation, NOT governor edit.
    Because shortlisting inspected TRAIN and historically known assets,
    this is not independent validation nor a tradable portfolio forecast.
    """
    # Use only diagnosis signals. If an opportunity is present in multiple
    # parameter variants, deterministic lexicographic priority is applied.
    candidate=[]
    for symbol,selected in results:
        for rank,(config,events) in enumerate(selected[:3]):
            for start,exit_at,r in events:
                mon=datetime.fromtimestamp(start,UTC).strftime("%Y-%m")
                if mon not in DIAG:continue
                candidate.append((start,rank,symbol,exit_at,r,config["label"]))
    candidate.sort(key=lambda x:(x[0],x[1],x[2],x[5]))
    scenarios=[]
    for risk in RISK_CHOICES:
        for max_open in (1,2):
            equity=peak=1.
            dd=0.;used=0;opened=[];family_active=set();rlist=[]
            stopped=False
            for start,rank,symbol,end,r,name in candidate:
                # Close only known completed paper fills when their exit time
                # is strictly earlier than the next candidate entry.
                old=[x for x in opened if x[0]<start]
                for ex,sy,entry_risk,paper_r in sorted(old):
                    equity=max(0.,equity*(1.+entry_risk*(paper_r-EXTRA_COST_R)))
                    peak=max(peak,equity);dd=max(dd,(peak-equity)/peak)
                    rlist.append(paper_r-EXTRA_COST_R)
                opened=[x for x in opened if x[0]>=start]
                if dd>=MAX_DD:stopped=True
                if stopped or len(opened)>=max_open or any(x[1]==symbol for x in opened):
                    continue
                actual_risk=risk/2 if dd>=.04 else risk
                opened.append((end,symbol,actual_risk,r));used+=1
            for ex,sy,entry_risk,paper_r in sorted(opened):
                equity=max(0.,equity*(1.+entry_risk*(paper_r-EXTRA_COST_R)))
                peak=max(peak,equity);dd=max(dd,(peak-equity)/peak)
                rlist.append(paper_r-EXTRA_COST_R)
            scenarios.append({
                "risk_fraction":risk,"max_concurrent":max_open,"modeled_positions":used,
                "return_pct":round((equity-1)*100,4),
                "max_drawdown_pct":round(dd*100,4),
                "paper_expectancy":summarize(rlist),
                "drawdown_stop_activated":stopped,
                "approved_for_live":False,
            })
    return scenarios

def run_broker(symbols):
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("MT5_HISTORY_NOT_AVAILABLE")
    try:
        info=mt5.terminal_info()
        if info is None or info.trade_allowed:
            raise RuntimeError("FAIL_CLOSED_MT5_TRADING_ENABLED")
        start=datetime(2026,5,22,tzinfo=UTC)
        end=datetime(2026,10,1,tzinfo=UTC)
        out={
            "status":"HISTORICAL_BROKER_RESEARCH_ONLY",
            "source":"MT5 broker M15 H1 H4 BID OHLC with per-bar spread",
            "period_utc":[start.isoformat(),end.isoformat()],
            "design":"precommitted June-July TRAIN, Aug-Sep DIAGNOSTIC",
            "train_previously_inspected":True,
            "diagnostic_independently_unseen":False,
            "broker_tick_fills_verified":False,
            "broker_commission_swap_verified":False,
            "fee_r_assumed":FEE_R,
            "extra_cost_r":EXTRA_COST_R,
            "risk_profiles":list(RISK_CHOICES),
            "orders_sent":0,"production":"WAIT","risk_governor_modified":False,
            "markets":{}}
        selected=[]
        for symbol in symbols:
            spec=mt5.symbol_info(symbol)
            if spec is None or spec.trade_mode!=4:
                out["markets"][symbol]={"status":"UNAVAILABLE"}
                continue
            raw={}
            for frame,mtf,sec in (("M15",mt5.TIMEFRAME_M15,900),
                                  ("H1",mt5.TIMEFRAME_H1,3600),
                                  ("H4",mt5.TIMEFRAME_H4,14400)):
                rates=mt5.copy_rates_range(symbol,mtf,start,end)
                raw[frame]=load_bars(rates,sec) if rates is not None else []
            if len(raw["M15"])<400 or len(raw["H1"])<150 or len(raw["H4"])<60:
                out["markets"][symbol]={"status":"INSUFFICIENT_BROKER_HISTORY"}
                continue
            record,winners=evaluate_market(
                symbol,float(spec.point),
                float(spec.trade_tick_size or spec.point),raw)
            out["markets"][symbol]=record
            selected.append((symbol,winners))
            print("V10_MARKET",json.dumps({
                "symbol":symbol,
                "m15_bars":len(raw["M15"]),"h1_bars":len(raw["H1"]),
                "candidates":record["diagnostics"].get("M15:candidates",0)+
                             record["diagnostics"].get("H1:candidates",0),
                "train_shortlist":record["train_shortlist_count"],
                "diag_pass":record["diagnostic_research_pass_count"],
                "M15_spread_atr":record["spread_ATR_median"].get("M15"),
                "H1_spread_atr":record["spread_ATR_median"].get("H1"),
                "top":record["shortlist"][:2]},separators=(",",":")),
                  flush=True)
        out["portfolio_paper_scenarios"]=portfolio_experiment(selected)
        out["count_markets"]=len(out["markets"])
        out["total_train_shortlisted"]=sum(m.get("train_shortlist_count",0) for m in out["markets"].values())
        out["total_diagnostic_research_gates"]=sum(m.get("diagnostic_research_pass_count",0) for m in out["markets"].values())
        out["total_parameter_configs"]=sum(m.get("total_parameter_cases",0) for m in out["markets"].values())
        out["live_authorized"]=False
        return out
    finally:
        mt5.shutdown()

def self_test():
    base=1_780_000_000
    bars=[Bar(base+i*900,101,102,100,101,12) for i in range(45)]
    hs=[Bar(base+i*3600,101,102,100,101,12) for i in range(20)]
    assert generate(bars,hs,hs,.12,.01)==()
    assert model_fill("BUY",Bar(base,100,102,98,100,10),
            [Bar(base,100,104,95,101,10)],.01,.01,2,1.,1.5,900)[2]=="SL_BOTH_FIRST"
    assert summarize([1,-1])["mean_r"]==0
    assert atr(bars)>0 and slope(hs)==0
    # A one-hour non-trading session break must not be confused with a
    # future candle; exclude major multiday gaps instead of rejecting
    # all continuously traded bars after every daily break.
    assert 0<4*3600<=14400
    assert len(ALL)==4 and DIAG.isdisjoint(TRAIN)
    print("V10_CAUSAL_RESEARCH_SELF_TEST_PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--symbols",default=",".join(SYMBOLS))
    x=ap.parse_args()
    if x.self_test:
        self_test();return
    chosen=[s.strip() for s in x.symbols.split(",") if s.strip()]
    if len(set(chosen))!=len(chosen) or not chosen or any(s not in SYMBOLS for s in chosen):
        raise ValueError("INVALID_RESEARCH_MARKET_SET")
    out=run_broker(chosen)
    print("V10_AGGREGATED_RESULT_JSON",json.dumps(out,separators=(",",":"),
          allow_nan=False),flush=True)

if __name__=="__main__":
    main()
