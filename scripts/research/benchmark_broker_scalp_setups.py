"""KATARINA broker-aware independent scalp-family tick replay.

No order_send/order_check/order placement. Broker metadata comes from demo
Valetax MT5 .vx catalog. Historical bid/ask and closed M1/M5 rates used.
Published Standard $0 commission is a *schedule assumption* absent deal proof.
"""
from __future__ import annotations
import argparse
from bisect import bisect_right
from collections import Counter
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from statistics import mean
import sys

BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/"src"))
from katarina.intelligence.scalp_pattern_candidates import propose_family,FAMILIES
from replay_historical_tick_stops import historical_path,simulate
from historical_shadow_ticks import bars,first_quote,intact

UTC=timezone.utc
PERIODS=(("development_aug","2026-08-16","2026-09-01"),
         ("development_sep","2026-09-15","2026-10-01"),
         ("diagnostic_oct","2026-10-01","2026-10-10"))
SYMBOLS=("XAUUSD.vx","NAS100.vx","US30.vx","JPN225.vx",
         "EURUSD.vx","GBPUSD.vx","USDJPY.vx")
MAX_SPREAD_ATR=.50
EXITS=((1.0,1.0),(1.5,1.0),(2.0,1.0),(2.0,1.5))
ADVERSE_TICK_PER_SIDE=(0,1,3)
HOLD=1800

def stamp(text):
    return datetime.fromisoformat(text).timestamp()

def ema_series(rates):
    result=[]
    val=None
    alpha=2/21
    for r in rates:
        val=float(r["close"]) if val is None else val+alpha*(float(r["close"])-val)
        result.append(val)
    return result

def quick_prefilter(m1,ema,index):
    cur=m1[index]; prev=m1[index-1]
    w=cur["high"]-cur["low"]
    if not w or abs(cur["close"]-cur["open"])<.30*w:
        return False
    if cur["tick_volume"]<.85*mean(r["tick_volume"] for r in m1[index-20:index]):
        return False
    bullish=cur["close"]>cur["open"] and cur["close"]>cur["low"]+.65*w
    bearish=cur["close"]<cur["open"] and cur["close"]<cur["high"]-.65*w
    if not bullish and not bearish:
        return False
    # Necessary conditions only, not an additional learned filter.
    prior=m1[index-12:index]
    lo=min(x["low"] for x in prior)
    hi=max(x["high"] for x in prior)
    crossing=(bullish and prev["close"]<=ema[index-1] and cur["close"]>ema[index] or
              bearish and prev["close"]>=ema[index-1] and cur["close"]<ema[index])
    sweep=(bullish and cur["low"]<lo and cur["close"]>lo or
           bearish and cur["high"]>hi and cur["close"]<hi)
    retest=(bullish and prev["close"]>max(b["high"] for b in m1[index-13:index-1]) and cur["low"]<=prev["high"] or
            bearish and prev["close"]<min(b["low"] for b in m1[index-13:index-1]) and cur["high"]>=prev["low"])
    # Include the original breakout family without using future candles.
    impulse=(bullish and cur["close"]>max(b["high"] for b in m1[index-6:index]) or
             bearish and cur["close"]<min(b["low"] for b in m1[index-6:index]))
    return crossing or sweep or retest or impulse

def slip_ticks_and_replay(quotes,side,atr,tp,sl,ticks_count,tick_size):
    """Two-sided adverse execution perturbation, no optimistic stop rounding."""
    if not quotes:return dict(status="NO_TICKS")
    opened,bid,ask=quotes[0]
    entry_worse=ticks_count*tick_size
    # The reference entry quote is still immutable in the evidence; this
    # separate altered first quote is a conditional worse-execution scenario.
    changed=list(quotes)
    changed[0]=(opened,
       bid-entry_worse if side=="SELL" else bid,
       ask+entry_worse if side=="BUY" else ask)
    result=simulate(changed,side,atr,tp,sl,extra_cost_bps=0)
    if result["status"]!="CLOSED":return result
    # adverse exit slippage of N broker ticks beyond observed exit bid/ask
    exit_worse=ticks_count*tick_size
    original_mid=(bid+ask)/2
    orig_sl=sl*atr
    result["quoted_delta"]-=exit_worse
    result["quoted_bps"]=result["quoted_delta"]/original_mid*10000
    result["stressed_bps"]=result["quoted_bps"]
    result["stressed_r"]=result["quoted_delta"]/orig_sl
    result["entry_slippage_ticks"]=ticks_count
    result["exit_slippage_ticks"]=ticks_count
    result["actual_exit_price_assumed"]+=(-exit_worse if side=="BUY" else exit_worse)
    return result

def make_summary(samples):
    done=[s for s in samples if s["status"]=="CLOSED"]
    bad=Counter(s["status"] for s in samples if s["status"]!="CLOSED")
    if not done:
        return dict(candidates=len(samples),closed=0,missing=dict(bad),
                    mean_r=None,profit_factor=None,win_fraction=None,
                    sum_nominal_minlot_usd=None,largest_peak_to_trough_r=None,
                    enough_evidence=False)
    values=[s["R"] for s in done]
    gains=sum(v for v in values if v>0)
    losses=-sum(v for v in values if v<0)
    max_draw=peak=equity=0.
    for val in values:
        equity+=val
        peak=max(peak,equity)
        max_draw=max(max_draw,peak-equity)
    days={s["signal_close_utc"][:10] for s in done}
    dollars=[s["usd_minlot"] for s in done if s["usd_minlot"] is not None]
    # USD-only profit calculations use account currency. For JPY pairs
    # we retain R only, not contemporary conversion as historical USD cash.
    return dict(candidates=len(samples),closed=len(done),
       outcome_coverage=len(done)/len(samples) if samples else 0,
       missing=dict(bad),days=len(days),
       mean_r=mean(values),profit_factor=gains/losses if losses else None,
       win_fraction=sum(v>0 for v in values)/len(values),
       sum_nominal_minlot_usd=sum(dollars) if len(dollars)==len(done) else None,
       largest_peak_to_trough_r=max_draw,
       exits=dict(Counter(s["exit_reason"] for s in done)),
       enough_evidence=len(done)>=30 and len(days)>=10 and len(done)/len(samples)>=.80)

def iterate_symbol(mt5,symbol,period):
    phase,start,end=period
    from_dt=datetime.fromisoformat(start).replace(tzinfo=UTC)
    until=datetime.fromisoformat(end).replace(tzinfo=UTC)
    info=mt5.symbol_info(symbol)
    if info is None or info.trade_mode not in (1,2,4):
        return [],dict(reason="broker_not_tradable")
    if not mt5.symbol_select(symbol,True):
        return [],dict(reason="select_failed")
    t0=from_dt-timedelta(days=3)
    raw1=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,t0,until)
    raw5=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M5,t0,until)
    if raw1 is None or raw5 is None:
        return [],dict(reason="history_unavailable",api_error=mt5.last_error())
    m1,m5=bars(raw1),bars(raw5)
    five_closes=[int(r["time"]+300) for r in m5]
    ema=ema_series(m1)
    last_open=dict.fromkeys([(fam,side) for fam in FAMILIES for side in ("BUY","SELL")],float("-inf"))
    events=[]
    counts=Counter()
    for i in range(121,len(m1)):
        close=m1[i]["time"]+60
        if close<from_dt.timestamp() or close>=until.timestamp():
            continue
        counts["closed_bars_checked"]+=1
        if not quick_prefilter(m1,ema,i):
            continue
        counts["quick_prefilter_pass"]+=1
        j=bisect_right(five_closes,close)-1
        if j<119 or not intact(m1[i-119:i+1],60) or not intact(m5[j-119:j+1],300):
            counts["missing_full_causal_history"]+=1
            continue
        now=datetime.fromtimestamp(close,UTC)
        try:
            proposals=propose_family(m1[i-119:i+1],m5[j-119:j+1],now)
        except (ValueError,KeyError,ZeroDivisionError):
            counts["pattern_feature_error"]+=1
            continue
        if not proposals:continue
        for candidate in proposals:
            family,side,atr=candidate["family"],candidate["side"],candidate["atr"]
            counts["family_"+family]+=1
            if side not in ({4:("BUY","SELL"),1:("BUY",),2:("SELL",)}[info.trade_mode]):
                counts["broker_direction_denied"]+=1
                continue
            if close<last_open[(family,side)]:
                counts["overlap_30m"]+=1
                continue
            if atr<=0 or not isfinite(atr):
                counts["ATR_invalid"]+=1
                continue
            # Entry attempts are not instantaneous at the closed candle;
            # 250ms decision+dispatch delay, 30s quote-availability budget.
            entry,why=first_quote(mt5,symbol,close+.250,30.)
            if why:
                counts["entry_"+why]+=1
                continue
            ratio=(entry["ask"]-entry["bid"])/atr
            if ratio>MAX_SPREAD_ATR or ratio<0:
                counts["quote_cost_above_research_max"]+=1
                continue
            broker_min_stop=float(info.trade_stops_level)*float(info.point)
            if min(sl*atr for tp,sl in EXITS)<=broker_min_stop+float(info.trade_tick_size):
                counts["stop_broker_minimum_violation"]+=1
                continue
            evidence=dict(symbol=symbol,family=family,side=side,phase=phase,
                signal_close_utc=now.isoformat(),signal_time=close,
                entry_time_utc=datetime.fromtimestamp(entry["time"],UTC).isoformat(),
                entry_bid=entry["bid"],entry_ask=entry["ask"],
                entry_spread_div_atr=ratio,signal_atr=atr,
                context_adx=candidate["context_adx"],volume_ratio=candidate["volume_ratio"],
                broker_min_stop_price=broker_min_stop,
                current_trade_mode=int(info.trade_mode),
                current_broker_contract_size=float(info.trade_contract_size),
                current_min_lot=float(info.volume_min),
                current_tick_size=float(info.trade_tick_size),
                currency_profit=info.currency_profit,
                current_account_profit_conversion_not_historical=True)
            ticks,why=historical_path(mt5,symbol,
                dict(entry_tick_utc=evidence["entry_time_utc"],
                     entry_bid=entry["bid"],entry_ask=entry["ask"]))
            if why:
                counts["path_"+why]+=1
                continue
            digest=sha256(json.dumps(ticks,separators=(",",":"),allow_nan=False).encode()).hexdigest()
            last_open[(family,side)]=entry["time"]+HOLD
            for tp,sl in EXITS:
                for slip in ADVERSE_TICK_PER_SIDE:
                    exit_result=slip_ticks_and_replay(ticks,side,atr,tp,sl,
                                                      slip,float(info.trade_tick_size))
                    R=exit_result.get("stressed_r")
                    usd=None
                    if (exit_result["status"]=="CLOSED" and info.currency_profit=="USD"):
                        entry_adjusted=(entry["ask"]+slip*info.trade_tick_size
                            if side=="BUY" else entry["bid"]-slip*info.trade_tick_size)
                        exit_assumed=exit_result["actual_exit_price_assumed"]
                        usd=mt5.order_calc_profit(
                            mt5.ORDER_TYPE_BUY if side=="BUY" else mt5.ORDER_TYPE_SELL,
                            symbol,info.volume_min,entry_adjusted,exit_assumed)
                    rec=dict(**evidence,tp_atr=tp,sl_atr=sl,
                        adverse_slippage_each_side_ticks=slip,
                        tick_path_sha256=digest,ticks_available=len(ticks),
                        stop_target_are_counterfactual=True,
                        strategy_live_authorized=False,trade_filled=False,
                        R=R,usd_minlot=usd,
                        status=exit_result["status"],
                        exit_reason=exit_result.get("exit_reason"),
                        exit_time_utc=exit_result.get("close_time_utc"),
                        exit_assumed_price=exit_result.get("actual_exit_price_assumed"),
                        nominal_risk_price=sl*atr)
                    events.append(rec)
            counts["candidate_eligible_quote_path"]+=1
    return events,dict(counts)

def execute(args):
    import MetaTrader5 as mt5
    if not mt5.initialize(args.terminal,timeout=20000):
        raise RuntimeError("research_mt5_init_failed "+str(mt5.last_error()))
    try:
        account=mt5.account_info()
        manifest=dict(
            broker_company=getattr(account,"company","UNKNOWN"),
            broker_account_currency=getattr(account,"currency","UNKNOWN"),
            broker_account_trade_mode=getattr(account,"trade_mode",-1),
            broker_account_leverage=getattr(account,"leverage",None),
            inferred_standard_suffix=".vx",
            broker_website_standard_commission_per_lot_usd=0.,
            commission_is_published_schedule_not_account_deal_verified=True,
            no_real_slippage_execution_sample_available=True)
        symbols=args.symbols.split(",")
        rows=[]
        counter={}
        for symbol in symbols:
            for period in PERIODS:
                result,diag=iterate_symbol(mt5,symbol,period)
                rows+=result
                counter[symbol+"|"+period[0]]=diag
                print(json.dumps(dict(symbol=symbol,phase=period[0],
                    eligible_events=len(result)//12,diagnostics=diag)),flush=True)
    finally:
        mt5.shutdown()
    summaries=[]
    for phase,start,end in PERIODS:
        for symbol in args.symbols.split(","):
            for family in FAMILIES:
                for side in ("BUY","SELL"):
                    for tp,sl in EXITS:
                        for slip in ADVERSE_TICK_PER_SIDE:
                            sample=[x for x in rows if x["phase"]==phase
                                and x["symbol"]==symbol and x["family"]==family
                                and x["side"]==side and x["tp_atr"]==tp
                                and x["sl_atr"]==sl and x["adverse_slippage_each_side_ticks"]==slip]
                            summaries.append(dict(
                                phase=phase,symbol=symbol,family=family,side=side,
                                tp_atr=tp,sl_atr=sl,adverse_slippage_each_side_ticks=slip,
                                **make_summary(sample)))
    obj=dict(report_version="broker_aware_independent_strategy_tick_study_v1",
        symbol_scope=args.symbols.split(","),date_windows_utc=PERIODS,
        reality="read_only_historical_counterfactual_not_real_pnl",
        historical_strategy_selection_bias=True,
        october_not_pristine_holdout=True,
        training_phase_names=["development_aug","development_sep"],
        evaluation_phase_name="diagnostic_oct",
        decision_latency_seconds=.25,
        maximum_quote_wait_seconds=30,
        max_historical_spread_atr=.5,stop_level_current_metadata=True,
        adverse_slippage_each_side_ticks=ADVERSE_TICK_PER_SIDE,
        hypothetical_exit_grid=EXITS,hold_seconds=HOLD,
        published_standard_commission_usd_per_lot_assumed=0.,
        no_actual_deal_commission_confirmation=True,
        lot_cash_pnl_uses_current_broker_calc_and_usd_quote_currency_only=True,
        historical_news_vintages_missing=True,portfolio_correlation_not_tested=True,
        model_promotion_allowed=False,live_execution_enabled=False,
        broker=manifest,per_scan=counter,
        input_references=[
          "https://valetax.com/account-types/standard/",
          "https://valetax.com/trading-instruments/metals/",
          "https://github.com/yeboster/liquidity-sweep-freqtrade",
          "https://github.com/guillemustafa-ux/ict-sweep-mss-fvg",
          "https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py"],
        result_count=len(rows),summaries=summaries,trials=rows)
    out=Path(args.output)
    if out.exists():raise FileExistsError("output_immutable_exists")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n")
    print("REPORT "+str(out),flush=True)
    research_candidates=[x for x in summaries if x["phase"]=="diagnostic_oct"
        and x["adverse_slippage_each_side_ticks"]==1
        and x["tp_atr"]==2.0 and x["sl_atr"]==1.0
        and x["closed"]>0]
    print("DIAGNOSTIC_OCT "+json.dumps(sorted(research_candidates,
         key=lambda x:(-x["closed"],x["symbol"],x["side"]))[:25]),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--terminal",default=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe")
    p.add_argument("--symbols",default=",".join(SYMBOLS))
    p.add_argument("--output",required=True)
    execute(p.parse_args())
if __name__=="__main__":
    main()
