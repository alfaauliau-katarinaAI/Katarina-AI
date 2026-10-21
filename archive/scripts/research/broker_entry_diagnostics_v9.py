"""KATARINA V9 read-only broker historical entry research.

Safe for ephemeral execution on a VPS with MT5 trading DISABLED.
No orders, credentials, account queries, file writes, or data upload.
Prints market-level aggregate model evidence as JSON to stdout.
For research, do not treat retrospective findings as independent OOS.
"""
from __future__ import annotations
from bisect import bisect_right
from collections import Counter, defaultdict, namedtuple
from datetime import datetime, timezone
import argparse
import json
import statistics

B = namedtuple("B", "time o h l c spread")
SYMBOLS = ("EURUSD.vx","GBPUSD.vx","USDJPY.vx","USDCHF.vx",
    "USDCAD.vx","AUDUSD.vx","NZDUSD.vx","EURGBP.vx","EURJPY.vx",
    "GBPJPY.vx","AUDJPY.vx","EURAUD.vx","XAUUSD.vx","BTCUSD.vx",
    "XTIUSD.vx","US30.vx","NAS100.vx")
FAMILIES = ("TREND_PULLBACK","BREAKOUT_RETEST",
    "LIQUIDITY_SWEEP_RECLAIM","RANGE_MEAN_REVERSION",
    "TREND_EXPANSION_V9","SWEEP_2C_CONFIRM_V9")
PERIODS = ("2026-06","2026-07","2026-08")
WINDOW_END = "2026-09-01"
BASE_FEE_R = .03
MORE_COST_R = .10
HOLD = 24


def median(values):
    return round(statistics.median(values), 5) if values else None


def atr(bars, length=14):
    if len(bars) < length + 1:
        return None
    tr = [max(bars[i].h - bars[i].l,
              abs(bars[i].h - bars[i-1].c),
              abs(bars[i].l - bars[i-1].c))
          for i in range(len(bars)-length, len(bars))]
    return sum(tr)/length


def regime(h1):
    a=atr(h1)
    if a is None or a <= 0 or len(h1)<16:
        return "UNKNOWN"
    slope=(h1[-1].c-h1[-7].c)/a
    return "TREND_UP" if slope>=1.3 else "TREND_DOWN" if slope<=-1.3 else "RANGE_OR_MIXED"


def proposals(m5, h1, point, spread_price):
    """Four V8 definitions plus two frozen, new, disjoint entry hypotheses.

    No access to any future prices or outcomes.
    Return (family, BUY/SELL, stop, target, context).
    """
    if len(m5)<30 or len(h1)<16:
        return ()
    a=atr(m5)
    if a is None or a<=0 or point<=0 or spread_price<0:
        return ()
    state=regime(h1)
    latest,prev=m5[-1],m5[-2]
    historical=m5[-22:-2]
    hi=max(x.h for x in historical)
    lo=min(x.l for x in historical)
    down=sum(x.c<x.o for x in m5[-8:-1])>=2
    up=sum(x.c>x.o for x in m5[-8:-1])>=2
    body=abs(latest.c-latest.o)
    result=[]
    def add(name,side,stop,rr=1.6,new=False):
        risk=latest.c-stop if side=="BUY" else stop-latest.c
        if risk<=max(3*point,2*spread_price) or risk>4*a:
            return
        target=latest.c+(risk*rr if side=="BUY" else -risk*rr)
        if target<=0:
            return
        result.append((name,side,stop,target,state))
    # V8: identical signal conditions, including <=20% spread/ATR veto.
    if spread_price/a<=.20:
        if state=="TREND_UP" and down and latest.c>prev.c and latest.c-latest.o>=.35*a:
            add("TREND_PULLBACK","BUY",min(x.l for x in m5[-8:]))
        if state=="TREND_DOWN" and up and latest.c<prev.c and latest.o-latest.c>=.35*a:
            add("TREND_PULLBACK","SELL",max(x.h for x in m5[-8:]))
        if state=="TREND_UP" and prev.c>hi+.1*a and latest.l<=hi and latest.c>hi and latest.c>latest.o:
            add("BREAKOUT_RETEST","BUY",min(latest.l,prev.l)-.1*a)
        if state=="TREND_DOWN" and prev.c<lo-.1*a and latest.h>=lo and latest.c<lo and latest.c<latest.o:
            add("BREAKOUT_RETEST","SELL",max(latest.h,prev.h)+.1*a)
        if state=="RANGE_OR_MIXED":
            lw=min(latest.o,latest.c)-latest.l
            uw=latest.h-max(latest.o,latest.c)
            if latest.l<lo-.08*a and latest.c>lo and lw>=.4*a:
                add("LIQUIDITY_SWEEP_RECLAIM","BUY",latest.l-.1*a)
            if latest.h>hi+.08*a and latest.c<hi and uw>=.4*a:
                add("LIQUIDITY_SWEEP_RECLAIM","SELL",latest.h+.1*a)
            if latest.c<lo+.3*a and latest.c>latest.o and prev.c<prev.o:
                add("RANGE_MEAN_REVERSION","BUY",min(latest.l,prev.l)-.1*a)
            if latest.c>hi-.3*a and latest.c<latest.o and prev.c>prev.o:
                add("RANGE_MEAN_REVERSION","SELL",max(latest.h,prev.h)+.1*a)
    # V9-A: a full-body closed breakout, H1 directional agreement.
    # Separate from V8 retest: expansion closes OUTSIDE last 20 M5 highs.
    if spread_price/a<=.33 and body>=.60*a:
        if state=="TREND_UP" and latest.c>hi+.15*a and latest.c>latest.o:
            add("TREND_EXPANSION_V9","BUY",latest.c-1.3*a,2.0,True)
        if state=="TREND_DOWN" and latest.c<lo-.15*a and latest.c<latest.o:
            add("TREND_EXPANSION_V9","SELL",latest.c+1.3*a,2.0,True)
    # V9-B: wait for a *second, completed* candle to confirm prior-bar sweep.
    # Previous sweep reference excludes the sweep bar and the current bar.
    if spread_price/a<=.33 and state=="RANGE_OR_MIXED":
        sweep_hi=max(x.h for x in m5[-23:-3])
        sweep_lo=min(x.l for x in m5[-23:-3])
        if prev.l<sweep_lo-.08*a and prev.c>sweep_lo and latest.c>prev.h:
            add("SWEEP_2C_CONFIRM_V9","BUY",min(prev.l,latest.l)-.1*a,1.8,True)
        if prev.h>sweep_hi+.08*a and prev.c<sweep_hi and latest.c<prev.l:
            add("SWEEP_2C_CONFIRM_V9","SELL",max(prev.h,latest.h)+.1*a,1.8,True)
    return tuple(result)


def to_h1(rows):
    """Only fully formed 12-candle hourly groups survive."""
    h1=[]
    group=[]
    group_end=None
    for bar in rows:
        block=((bar.time-1)//3600+1)*3600
        if block!=group_end:
            if len(group)==12 and group[-1].time==group_end and group[0].time==group_end-3300 and all(group[i].time-group[i-1].time==300 for i in range(1,12)):
                h1.append(B(group_end,group[0].o,max(x.h for x in group),min(x.l for x in group),group[-1].c,group[-1].spread))
            group=[]
            group_end=block
        group.append(bar)
    if len(group)==12 and group[-1].time==group_end and group[0].time==group_end-3300 and all(group[i].time-group[i-1].time==300 for i in range(1,12)):
        h1.append(B(group_end,group[0].o,max(x.h for x in group),min(x.l for x in group),group[-1].c,group[-1].spread))
    return h1


def fill(opportunity, entry, future, point, tick):
    """Bid M5 OHLC + observed historical bar spread; no true tick ordering."""
    name,side,stop,target,_=opportunity
    entry_spread=max(0,entry.spread)*point
    if side=="BUY":
        open_price=entry.o+entry_spread+tick
        risk=open_price-stop
        reward=target-open_price
    else:
        open_price=entry.o-tick
        stop+=entry_spread
        target+=entry_spread
        risk=stop-open_price
        reward=open_price-target
    if risk<=max(3*point,2*entry_spread) or reward/risk<.60:
        return None
    last=entry
    realized=None
    outcome="TIME"
    # Future includes entry bar. Do not drop an otherwise valid candidate
    # merely because a LATER market session has a gap.
    prev_time=entry.time-300
    for bar in future[:HOLD]:
        if bar.time-prev_time!=300:
            break
        prev_time=bar.time
        last=bar
        pxspread=max(0,bar.spread)*point
        op=bar.o if side=="BUY" else bar.o+pxspread
        high=bar.h if side=="BUY" else bar.h+pxspread
        low=bar.l if side=="BUY" else bar.l+pxspread
        sl=low<=stop if side=="BUY" else high>=stop
        tp=high>=target if side=="BUY" else low<=target
        if sl:
            realized=(min(op,stop)-tick if side=="BUY" else max(op,stop)+tick)
            outcome="SL_STOP_FIRST" if tp else "SL"
        elif tp:
            realized=target-tick if side=="BUY" else target+tick
            outcome="TP"
        else:
            realized=(bar.c-tick if side=="BUY" else bar.c+pxspread+tick)
        if sl or tp:
            break
    if realized is None:
        return None
    r=(realized-open_price)/risk if side=="BUY" else (open_price-realized)/risk
    return round(r-BASE_FEE_R,6),outcome,last.time


def metrics(values, cost=0.):
    if not values:
        return {"n":0,"mean_r":None,"pf":None,"win_pct":None}
    vals=[x-cost for x in values]
    pos=sum(x for x in vals if x>0)
    neg=-sum(x for x in vals if x<0)
    return dict(n=len(vals),mean_r=round(sum(vals)/len(vals),6),
                pf=round(pos/neg,4) if neg else None,
                win_pct=round(100*sum(x>0 for x in vals)/len(vals),2))


def evaluate(symbol,raw,point,tick_size,minimum_bars=200):
    rows=[B(int(b["time"])+300,float(b["open"]),float(b["high"]),
            float(b["low"]),float(b["close"]),int(b["spread"])) for b in raw]
    if len(rows)<minimum_bars:
        return None
    hs=to_h1(rows)
    hclock=[b.time for b in hs]
    grouped=defaultdict(list)
    reasons=Counter()
    active_until={}
    friction=[]
    for i in range(29,len(rows)-1):
        now=rows[i].time
        history=rows[i-29:i+1]
        if any(history[k].time-history[k-1].time!=300 for k in range(1,30)):
            reasons["signal_history_gap"]+=1
            continue
        j=bisect_right(hclock,now)
        if j<16 or rows[i+1].time!=now+300:
            reasons["h1_warmup_or_next_bar_missing"]+=1
            continue
        h1=hs[j-16:j]
        fee=max(0,rows[i].spread)*point
        a=atr(history)
        if a and a>0:
            friction.append(fee/a)
        candidates=proposals(history,h1,point,fee)
        reasons["total_candidates"]+=len(candidates)
        for item in candidates:
            family,side,_,_,reg=item
            key=(family,side)
            if active_until.get(key,0)>now:
                reasons["overlap_wait"]+=1
                continue
            settled=fill(item,rows[i+1],rows[i+1:i+1+HOLD],point,tick_size)
            if settled is None:
                reasons["invalid_entry_geometry"]+=1
                continue
            value,outcome,exit_time=settled
            active_until[key]=exit_time
            month=datetime.fromtimestamp(now,timezone.utc).strftime("%Y-%m")
            grouped[(family,side,month)].append(value)
    flat=defaultdict(list)
    monthly=defaultdict(dict)
    for (family,side,month),r in grouped.items():
        flat[(family,side)]+=r
        monthly[family+"/"+side][month]=metrics(r)
    # Monthly screen not a statistical proof or live-promotion license.
    return dict(
        candles=len(rows),first=rows[0].time,last=rows[-1].time,
        complete_h1_bars=len(hs),
        median_historical_spread_points=median([b.spread for b in rows if b.spread>0]),
        median_spread_to_m5_atr=median(friction),
        diagnostics=dict(reasons),
        by_strategy_side={
            family+"/"+side:{
                "base":metrics(vals),
                "extra_0_10R":metrics(vals,.10),
                "monthly":{
                    month:monthly[family+"/"+side].get(month,metrics([]))
                    for month in PERIODS},
                "triage_only":False}
            for (family,side),vals in sorted(flat.items())
        })


def broker_test(symbols,begin,end):
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("broker_history_unavailable")
    try:
        terminal=mt5.terminal_info()
        if terminal is None or terminal.trade_allowed:
            raise RuntimeError("FAIL_CLOSED_trading_must_be_disabled")
        result={
            "status":"BROKER_HISTORICAL_RESEARCH_ONLY",
            "period_utc_requested":[begin.isoformat(),end.isoformat()],
            "source":"MT5 broker M5 bid OHLC and historical spread points",
            "historical_spread_measured":True,
            "historical_ask_OHLC_observed":False,
            "fee_assumption_r":BASE_FEE_R,
            "extra_cost_sensitivity_r":MORE_COST_R,
            "broker_deals_or_real_commissions_verified":False,
            "independent_unseen_OOS":False,
            "orders_sent":0,"production_action":"WAIT","live_authorized":False,
            "markets":{}}
        for symbol in symbols:
            info=mt5.symbol_info(symbol)
            if info is None or info.trade_mode!=4:
                result["markets"][symbol]={"status":"SKIP_UNAVAILABLE_OR_DISABLED"}
                continue
            candles=mt5.copy_rates_range(
                symbol,mt5.TIMEFRAME_M5,begin,end)
            if candles is None or len(candles)<200:
                result["markets"][symbol]={"status":"SKIP_INSUFFICIENT_BROKER_BARS"}
                continue
            detail=evaluate(symbol,candles,float(info.point),
                            float(info.trade_tick_size or info.point))
            detail["status"]="RESEARCH_DIAGNOSTIC"
            detail["point"]=float(info.point)
            detail["tick_size"]=float(info.trade_tick_size or info.point)
            detail["broker_symbol"]=symbol
            # exclude account information, raw candles, and identifiable deals.
            result["markets"][symbol]=detail
            best=sorted([
                (v["extra_0_10R"]["mean_r"],v["extra_0_10R"]["n"],k)
                for k,v in detail["by_strategy_side"].items()
                if v["extra_0_10R"]["n"]>=20],
                reverse=True)[:2]
            print("BROKER_PAIR",json.dumps({
                "symbol":symbol,"bars":detail["candles"],
                "spread_pts":detail["median_historical_spread_points"],
                "median_spread_atr":detail["median_spread_to_m5_atr"],
                "hypotheses":detail["diagnostics"].get("total_candidates",0),
                "best_20trades_stressed":best},separators=(",",":")),
                flush=True)
        return result
    finally:
        mt5.shutdown()


def self_test():
    t=1_790_000_000
    bars=[B(t+i*300,100,101,99,100,3) for i in range(40)]
    h1=[B(t+i*3600,100,102,98,100,3) for i in range(20)]
    assert proposals(bars,h1,.01,.03)==()
    assert fill(("TEST","BUY",98,103,"RANGE"),B(t,100,103,97,100,3),
                [B(t,100,103,97,100,3)],.01,.01)[1]=="SL_STOP_FIRST"
    assert metrics([-1,2],.1)["mean_r"]==.4
    assert to_h1([B(t//3600*3600+(i+1)*300,1,2,.5,1,1)
                  for i in range(12)]) and len(
        to_h1([B(t//3600*3600+(i+1)*300,1,2,.5,1,1)
               for i in range(11)]))==0
    print("BROKER_RESEARCH_SELF_TEST_PASS",flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--symbols",default=",".join(SYMBOLS))
    ap.add_argument("--start",default="2026-06-01")
    ap.add_argument("--end",default=WINDOW_END)
    options=ap.parse_args()
    if options.self_test:
        self_test()
        return
    symbols=[x.strip() for x in options.symbols.split(",") if x.strip()]
    if not symbols or any(x not in SYMBOLS for x in symbols):
        raise ValueError("symbol_not_approved_for_broker_test")
    if options.start!="2026-06-01" or options.end!=WINDOW_END:
        raise ValueError("research_period_locked")
    start=datetime(2026,6,1,tzinfo=timezone.utc)
    end=datetime(2026,9,1,tzinfo=timezone.utc)
    result=broker_test(symbols,start,end)
    print("BROKER_AGGREGATE_JSON",json.dumps(result,separators=(",",":"),
        allow_nan=False),flush=True)

if __name__=="__main__":
    main()
