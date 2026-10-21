"""Independent per-symbol structural entry/exit tick laboratory.

Distinct playbooks per symbol, no common strategy reused across pairs.
Each proposal uses completed M1/M5 and same-day completed bars only.
True historical bid/ask are used for hypothetical entry/exit quotes; no
broker order routing. Scenario slippage is adverse ticks, not measured fills.
"""
from __future__ import annotations
import argparse
from bisect import bisect_right,bisect_left
from collections import Counter
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from statistics import mean
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from katarina.intelligence.perception.symbol_playbooks import SYMBOLS,CAPS,propose
from historical_shadow_ticks import first_quote,intact,bars
from replay_historical_tick_stops import normalized_ticks
UTC=timezone.utc
STRESSES=(0,1,3)
GAP_LIMIT_SECONDS=180.
DELAY_SECONDS=.250
TIMEOUT_QUOTE_SECONDS=90.
PERIODS=(("development_aug","2026-08-16","2026-09-01"),
         ("development_sep","2026-09-15","2026-10-01"),
         ("diagnostic_oct","2026-10-01","2026-10-10"))

def utc(ts):
    return datetime.fromtimestamp(ts,UTC).isoformat()

def tick_series(mt5,symbol,first_entry,hold_seconds):
    final=first_entry["time"]+hold_seconds+TIMEOUT_QUOTE_SECONDS
    raw=mt5.copy_ticks_range(symbol,datetime.fromtimestamp(first_entry["time"],UTC),
        datetime.fromtimestamp(final,UTC),mt5.COPY_TICKS_ALL)
    if raw is None:return None,"tick_history_api_failed"
    arr,error=normalized_ticks(raw)
    if error:return None,error
    if not arr:return None,"missing_history"
    spot=next((i for i,x in enumerate(arr)
       if abs(x[0]-first_entry["time"])<.002 and
          abs(x[1]-first_entry["bid"])<1e-7 and
          abs(x[2]-first_entry["ask"])<1e-7),None)
    if spot is None:return None,"entry_quote_not_reproduced"
    return arr[spot:],None

def simulate_structure(ticks,side,stop,target,hold,ticksize,slip_each):
    if not ticks:return dict(status="NO_TICKS")
    opened,bid,ask=ticks[0]
    entry=ask+ticksize*slip_each if side=="BUY" else bid-ticksize*slip_each
    risk=entry-stop if side=="BUY" else stop-entry
    reward=target-entry if side=="BUY" else entry-target
    if risk<=0 or reward<=0:return dict(status="INVALID_ENTRY_PRICES")
    delta=lambda b,a:(b-entry if side=="BUY" else entry-a)
    favorable=-float("inf")
    adverse=float("inf")
    last=opened
    deadline=opened+hold
    for t,b,a in ticks:
        if t<last or t-opened<-.002:return dict(status="UNSORTED_QUOTES")
        if t-last>GAP_LIMIT_SECONDS:return dict(status="QUOTE_DATA_GAP")
        last=t
        if t>deadline+TIMEOUT_QUOTE_SECONDS:return dict(status="EXPIRED_QUOTE")
        if not (isfinite(b) and isfinite(a) and b>0 and a>=b):
            return dict(status="INVALID_MARKET_QUOTE")
        p=b if side=="BUY" else a
        excursion=delta(b,a)
        favorable=max(favorable,excursion)
        adverse=min(adverse,excursion)
        if t>=deadline:
            why="TIME";exit_price=p
        elif (side=="BUY" and p<=stop) or (side=="SELL" and p>=stop):
            why="SL";exit_price=p # unfavorable stop jumps retained
        elif (side=="BUY" and p>=target) or (side=="SELL" and p<=target):
            why="TP";exit_price=target # cap favorable gap
        else:continue
        # Extra execution slip, charged on exit as well as entry.
        exit_price+=(-ticksize*slip_each if side=="BUY" else ticksize*slip_each)
        net=(exit_price-entry if side=="BUY" else entry-exit_price)
        return dict(status="CLOSED",exit_reason=why,
            entry_hypothetical_price=entry,exit_hypothetical_price=exit_price,
            close_time_utc=utc(t),hold_seconds=t-opened,
            effective_risk_price=risk,effective_reward_price=reward,
            R=net/risk,mfe_R=max(0.,favorable/risk),mae_R=min(0.,adverse/risk),
            nominal_target_R=reward/risk,entry_spread=(ask-bid),
            adverse_entry_ticks=slip_each,adverse_exit_ticks=slip_each)
    return dict(status="EXIT_QUOTE_MISSING")

def scan(mt5,symbol,phase,start,end,max_entries=10000,rule_fn=propose,caps=CAPS):
    start_date=datetime.fromisoformat(start).replace(tzinfo=UTC)
    end_date=datetime.fromisoformat(end).replace(tzinfo=UTC)
    info=mt5.symbol_info(symbol)
    if info is None or info.trade_mode not in (1,2,4):
        return [],dict(reason="symbol_unavailable_or_currently_not_tradable")
    if not mt5.symbol_select(symbol,True):
        return [],dict(reason="symbol_subscription_failed")
    begin=start_date-timedelta(days=4)
    m1_raw=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,begin,end_date)
    m5_raw=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M5,begin,end_date)
    if m1_raw is None or m5_raw is None:
        return [],dict(reason="rates_unavailable",last_error=mt5.last_error())
    minute,five=bars(m1_raw),bars(m5_raw)
    m5_close=[int(b["time"]+300) for b in five]
    m1_open=[int(b["time"]) for b in minute]
    counters=Counter()
    completed=[]
    lockout=-float("inf")
    for i in range(120,len(minute)):
        signal_time=minute[i]["time"]+60
        if not start_date.timestamp()<=signal_time<end_date.timestamp():
            continue
        counters["complete_candles_checked"]+=1
        if signal_time<lockout:
            counters["same_symbol_position_lockout"]+=1
            continue
        j=bisect_right(m5_close,signal_time)-1
        if j<119:continue
        m1_view=minute[i-119:i+1]
        m5_view=five[j-119:j+1]
        # JPN225 broker session often begins ~01:01 UTC and has a
        # documented overnight hiatus. Requiring 120 contiguous M1/M5
        # bars across that market closure incorrectly removes every
        # opening-range event. Alternative JPN logic only reads the first
        # 30 minutes of the actual observed session, so verify the *last*
        # 35 M1 and 6 M5 bars are contiguous instead. Retain 120 earlier
        # bars as causal context without forward filling missing prices.
        def contiguous_tail(rows,seconds,length):
            tail=rows[-length:]
            return len(tail)==length and all(
                0<tail[n]["time"]-tail[n-1]["time"]<=seconds*2
                for n in range(1,length))
        gap_safe=(contiguous_tail(m1_view,60,35)
                  and contiguous_tail(m5_view,300,6)
                  if caps is not CAPS and symbol=="JPN225.vx" else
                  intact(m1_view,60) and intact(m5_view,300))
        if not gap_safe:
            counters["bar_warmup_incomplete"]+=1
            continue
        current_day=int(minute[i]["time"])//86400*86400
        first_day=bisect_left(m1_open,current_day)
        day=minute[first_day:i+1]
        now=datetime.fromtimestamp(signal_time,UTC)
        try:
            offers=rule_fn(symbol,m1_view,m5_view,day,now)
        except ValueError:
            counters["invalid_candidate_data"]+=1
            continue
        if not offers:continue
        # Pre-registered symbol playbook is expected to offer only one side,
        # if multiple exist, skip instead of optimization/choice.
        if len(offers)!=1:
            counters["ambiguous_side"]=len(offers)
            continue
        candidate=offers[0]
        if candidate["side"] not in (
            ("BUY","SELL") if info.trade_mode==4 else
            ("BUY",) if info.trade_mode==1 else ("SELL",)):
            counters["side_broker_disallowed"]+=1
            continue
        counters["playbook_technical_setup"]+=1
        quote,why=first_quote(mt5,symbol,signal_time+DELAY_SECONDS,30.)
        if why:
            counters["entry_"+why]+=1
            continue
        atr=candidate["signal_atr"]
        spread=quote["ask"]-quote["bid"]
        if spread/atr>caps[symbol]:
            counters["spread_atr_guard_reject"]+=1
            continue
        entry=quote["ask"] if candidate["side"]=="BUY" else quote["bid"]
        stop,target=candidate["hypothetical_stop"],candidate["hypothetical_target"]
        risk=(entry-stop if candidate["side"]=="BUY" else stop-entry)
        reward=(target-entry if candidate["side"]=="BUY" else entry-target)
        min_stop=info.trade_stops_level*info.point
        if risk<=min_stop+info.trade_tick_size*4:
            counters["invalid_broker_stop_minimum"]+=1
            continue
        if reward<=0 or reward/risk<1.05:
            counters["structure_target_no_margin"]+=1
            continue
        if spread/reward>.30:
            counters["spread_exceeds_30pct_of_target"]+=1
            continue
        if risk>4*atr:
            counters["structural_risk_too_wide"]+=1
            continue
        hold=candidate["max_holding_minutes"]*60
        ticks,why=tick_series(mt5,symbol,quote,hold)
        if why:
            counters["tick_path_"+why]+=1
            continue
        lockout=quote["time"]+hold
        evidence=dict(symbol=symbol,family=candidate["family"],
            side=candidate["side"],research_window=phase,
            entry_signal_close_utc=now.isoformat(),
            quote_entry_utc=utc(quote["time"]),
            broker_quote_entry_bid=quote["bid"],broker_quote_entry_ask=quote["ask"],
            entry_spread_div_atr=spread/atr,
            spread_target_fraction=spread/reward,
            signal_atr=atr,stop_price=stop,target_price=target,
            structural_reference=candidate["reference_structure"],
            max_hold_seconds=hold,current_broker_stop_minimum=min_stop,
            current_broker_tick_size=info.trade_tick_size,
            current_min_lot=info.volume_min,
            broker_spec_is_current_not_historical=True,
            historical_quote_sha256=sha256(json.dumps(
                ticks,separators=(",",":"),allow_nan=False).encode()).hexdigest(),
            historical_tick_count=len(ticks),
            production_orders_enabled=False,can_trade_live=False)
        for slip in STRESSES:
            outcome=simulate_structure(ticks,candidate["side"],stop,target,hold,
                      info.trade_tick_size,slip)
            completed.append(dict(**evidence,slippage_each_side_ticks=slip,
                    **outcome))
        counters["unique_entry_paths_replayed"]+=1
        if counters["unique_entry_paths_replayed"]>=max_entries:
            counters["sample_cap_reached"]+=1
            break
    return completed,dict(counters)

def group_report(rows, registry=SYMBOLS):
    groups=[]
    for (symbol,phase,slip),arr in sorted(
        ((k,[x for x in rows if (x["symbol"],x["research_window"],x["slippage_each_side_ticks"])==k])
        for k in {(r["symbol"],r["research_window"],r["slippage_each_side_ticks"]) for r in rows}),
        key=lambda x:x[0]):
        good=[r for r in arr if r["status"]=="CLOSED"]
        ret=[r["R"] for r in good]
        ups=sum(v for v in ret if v>0)
        downs=-sum(v for v in ret if v<0)
        groups.append(dict(symbol=symbol,phase=phase,slippage_ticks_each_side=slip,
            family=registry[symbol],entries=len(arr),complete=len(good),
            UTC_days=len(set(x["entry_signal_close_utc"][:10] for x in good)),
            mean_R=mean(ret) if ret else None,
            profit_factor=ups/downs if downs else None,
            success_rate=sum(x>0 for x in ret)/len(ret) if ret else None,
            avg_MFE_R=mean(x["mfe_R"] for x in good) if good else None,
            avg_MAE_R=mean(x["mae_R"] for x in good) if good else None,
            exits=dict(Counter(x["exit_reason"] for x in good)),
            missing=dict(Counter(x["status"] for x in arr if x["status"]!="CLOSED")),
            validated=False))
    return groups

def main():
    import MetaTrader5 as mt5
    p=argparse.ArgumentParser()
    p.add_argument("--terminal",default=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe")
    p.add_argument("--research-playbook-arm",choices=("original","alternatives"),default="original")
    p.add_argument("--symbols",default="XAUUSD.vx,US30.vx")
    p.add_argument("--output",required=True)
    p.add_argument("--max-entries-per-symbol-window",type=int,default=10000)
    p.add_argument("--window-label")
    p.add_argument("--window-start")
    p.add_argument("--window-end")
    args=p.parse_args()
    custom=(args.window_label,args.window_start,args.window_end)
    if any(custom) and not all(custom):
        p.error("custom historical window requires label, start, end together")
    if all(custom):
        a=datetime.fromisoformat(args.window_start).replace(tzinfo=UTC)
        b=datetime.fromisoformat(args.window_end).replace(tzinfo=UTC)
        if b<=a or b>=datetime.now(UTC) or len(args.window_label)>40:
            p.error("only fully completed bounded historical windows are allowed")
        periods=(custom,)
    else:
        periods=PERIODS
    if args.research_playbook_arm=="alternatives":
        from katarina.intelligence.perception import alternative_symbol_playbooks as arm
        registry,caps,rule_fn=arm.SYMBOLS,arm.CAPS,arm.propose
    else:
        registry,caps,rule_fn=SYMBOLS,CAPS,propose
    request=[s.strip() for s in args.symbols.split(",")]
    if any(s not in registry for s in request) or len(set(request))!=len(request):
        p.error("all broker symbols must have their own registered, unique playbook")
    out=Path(args.output)
    if out.exists():raise FileExistsError("output_file_immutable")
    if not mt5.initialize(args.terminal,timeout=25000):
        raise RuntimeError("read_only_research_terminal_unavailable")
    try:
        results=[];counts={}
        for symbol in request:
            for window in periods:
                rows,diag=scan(mt5,symbol,*window,
                    max_entries=args.max_entries_per_symbol_window,
                    rule_fn=rule_fn,caps=caps)
                results+=rows
                counts[symbol+"|"+window[0]]=diag
                print(json.dumps(dict(symbol=symbol,phase=window[0],
                    entries=len(rows)//len(STRESSES),counts=diag)),flush=True)
    finally:
        mt5.shutdown()
    doc=dict(kind="distinct_per_symbol_research_playbooks_v1",
       live_execution_enabled=False,model_promotion_allowed=False,
       note="Different strategy & TP/SL structures per instrument; no generic fallbacks.",
       inputs="closed_MT5_M1_M5_bars_and_actual_bid_ask_ticks",
       chrono_periods_utc=periods,
       historically_not_untouched_holdout=True,
       actual_executed_fills=False,broker_fees_not_measured=True,
       slippage_stress_ticks_each_side=STRESSES,
       no_cross_symbol_strategy_transfer=True,
       symbol_strategies={s:registry[s] for s in request},
       research_playbook_arm=args.research_playbook_arm,
       diagnostics=counts,total_unique_quote_paths=len(results)//len(STRESSES),
       groups=group_report(results,registry),trials=results)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("REPORT "+str(out))
    print("GROUPS "+json.dumps(doc["groups"]),flush=True)

if __name__=="__main__":
    main()
