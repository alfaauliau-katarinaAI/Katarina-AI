"""Fail-closed BID/ASK tick path reconciliation of EXISTING native-brain signals.

No MT5 dependency. Runner supplies real broker tick rows and M5 BID candle.
The signal is fixed BEFORE retrieving future quotes; no recalibration of
the signal, its SL/TP, spread threshold, or strategy is permitted.

Requires first entry bar BID OHLC/tick alignment to detect unsafe broker
clock assumptions, gap-free quote sequence, full horizon/SL/TP and actual
BID/ASK. Returns quote-simulated R, NEVER claimed broker fills/commissions.
"""
from __future__ import annotations

from math import isfinite
from statistics import mean

ENTRY_DELAY=90.
MAX_QUOTE_GAP=180.
HOLD_SECONDS=7200.
EXIT_GRACE=90.
MAX_TICKS=250000


def _bad(status, **extra):
    return {"status":status,"broker_fills_verified":False,
            "real_commission_verified":False,"live_eligible":False,**extra}


def _row(row):
    """MT5 numpy named rows or plain tuple (ms,bid,ask)."""
    try:
        if isinstance(row, tuple):
            ts,b,a=row
        else:
            ts,b,a=row["time_msc"],row["bid"],row["ask"]
        return (float(ts)/1000.,float(b),float(a))
    except (KeyError,ValueError,TypeError,IndexError):
        raise ValueError("unreadable_quote")


def tick_reconcile(signal, tick_rows, bid_candle, *,raw_offset_hours,
                   tick_size, extra_cost_r=.15):
    """Signal epoch is NORMALIZED research UTC; raw ticks use broker clock.

    A per-signal BID candle M5 open/high/low/close must match the first
    full 5min raw tick bar. This is an internal matching check, not a
    proof of stable historical DST over multiple months.
    """
    if signal["side"] not in ("BUY","SELL"):
        return _bad("SIGNAL_NOT_DIRECTIONAL")
    if not all(isinstance(x,(int,float)) and isfinite(x) for x in
               (signal["signal_at"],signal["sl"],signal["tp"],
                raw_offset_hours,tick_size,extra_cost_r)):
        return _bad("INVALID_SIGNAL_NUMBERS")
    if tick_size<=0 or not 0<=extra_cost_r<=.5:
        return _bad("INVALID_SIMULATION_SETTINGS")
    if raw_offset_hours!=int(raw_offset_hours) or abs(raw_offset_hours)>14:
        return _bad("BROKER_CLOCK_NOT_INTEGER_HOURS")
    if len(tick_rows)>MAX_TICKS:
        return _bad("TICK_PATH_TOO_LARGE",tick_count=len(tick_rows))
    if len(tick_rows)==0:
        return _bad("NO_TICK_HISTORY")
    raw_start=float(signal["signal_at"])+raw_offset_hours*3600
    raw_end=raw_start+HOLD_SECONDS+EXIT_GRACE
    # Candle key and OHLC from the same BROKER source, not a derived
    # converted record from another symbol or calendar date.
    try:
        candle_time=float(bid_candle["time"])
        op=float(bid_candle["open"])
        high=float(bid_candle["high"])
        low=float(bid_candle["low"])
        close=float(bid_candle["close"])
    except (KeyError,ValueError,TypeError):
        return _bad("M5_REFERENCE_BAR_MISSING")
    if (candle_time!=raw_start or not 0<low<=min(op,close)<=max(op,close)<=high):
        return _bad("BROKER_CANDLE_CLOCK_OR_OHLC_MISMATCH")
    prior=-float("inf");first_bar=[];quotes=[]
    for raw in tick_rows:
        try:t,bid,ask=_row(raw)
        except ValueError:return _bad("CORRUPTED_BROKER_TICK")
        if not all(isfinite(v) for v in (t,bid,ask)) or bid<=0 or ask<bid:
            return _bad("BAD_BID_ASK_QUOTE")
        if t<prior:
            return _bad("TICKS_NOT_MONOTONIC")
        prior=t
        if t<raw_start or t>raw_end:
            continue
        quotes.append((t,bid,ask))
        if t<raw_start+300:
            first_bar.append((t,bid,ask))
    if not first_bar or first_bar[0][0]>raw_start+ENTRY_DELAY:
        return _bad("FIRST_BAR_QUOTE_NOT_PROMPT")
    tolerance=max(tick_size*1.01,1e-7)
    opening=first_bar[0][1]
    bid_min=min(x[1] for x in first_bar)
    bid_max=max(x[1] for x in first_bar)
    bid_last=first_bar[-1][1]
    if (abs(opening-op)>tolerance or
        abs(bid_min-low)>tolerance or
        abs(bid_max-high)>tolerance or
        abs(bid_last-close)>tolerance):
        return _bad("BID_TICK_BAR_ALIGNMENT_FAILED",
            measured_bids=[round(opening,8),round(bid_max,8),
                           round(bid_min,8),round(bid_last,8)])
    start_index=next((i for i,x in enumerate(quotes)
                      if raw_start<=x[0]<=raw_start+ENTRY_DELAY),None)
    if start_index is None:
        return _bad("ENTRY_TICK_MISSING")
    start,bid,ask=quotes[start_index]
    side=signal["side"]
    entry=ask if side=="BUY" else bid
    stop=float(signal["sl"])
    take=float(signal["tp"])
    risk=(entry-stop) if side=="BUY" else (stop-entry)
    reward=(take-entry) if side=="BUY" else (entry-take)
    if not risk>2*tick_size or not reward>0:
        return _bad("TICK_ENTRY_GEOMETRY_UNTRADEABLE")
    if (ask-bid)>risk*.30:
        return _bad("TICK_ENTRY_SPREAD_EXCESSIVE")
    deadline=start+HOLD_SECONDS
    prior=start
    for j in range(start_index+1,len(quotes)):
        t,xbid,xask=quotes[j]
        if t-prior>MAX_QUOTE_GAP:
            return _bad("TICK_PATH_GAP",gap_seconds=round(t-prior,2))
        prior=t
        if t>deadline+EXIT_GRACE:
            return _bad("TIME_EXIT_QUOTE_MISSING")
        px=xbid if side=="BUY" else xask
        if t>=deadline:
            why="TIME";filled=px
        elif (px<=stop if side=="BUY" else px>=stop):
            why="SL";filled=px  # adverse gap uses observed worse price
        elif (px>=take if side=="BUY" else px<=take):
            why="TP";filled=min(px,take) if side=="BUY" else max(px,take)
        else:
            continue
        gross=(filled-entry)/risk if side=="BUY" else (entry-filled)/risk
        return {
            "status":"CLOSED_QUOTE_SIMULATION_ONLY","side":side,
            "entry_epoch_raw":round(start,3),"exit_epoch_raw":round(t,3),
            "raw_offset_hours_checked_on_entry_m5":raw_offset_hours,
            "entry_bid":bid,"entry_ask":ask,
            "exit_bid":xbid,"exit_ask":xask,
            "fill_price_model":filled,
            "hypothetical_sl":stop,"hypothetical_tp":take,
            "exit_reason":why,"risk_price":risk,
            "gross_quote_r":round(gross,6),
            "net_assumed_cost_r":round(gross-extra_cost_r,6),
            "tick_count":len(quotes),
            "entry_m5_tick_bid_match":True,
            "broker_fills_verified":False,"real_commission_verified":False,
            "live_eligible":False
        }
    return _bad("TICK_EXIT_PATH_INCOMPLETE",available_quotes=len(quotes))


def summarize_tick_reconciliation(rows):
    """All sampled hypotheses, failures *included* in coverage denominator."""
    from collections import Counter,defaultdict
    grouped=defaultdict(list)
    for row in rows:
        s=row["signal"];out=row["outcome"]
        key=(s["symbol"],s["method"],s["side"],s["regime"])
        grouped[key].append(out)
    cohorts=[]
    for (sym,method,side,regime),xs in sorted(grouped.items()):
        valid=[x["net_assumed_cost_r"] for x in xs
               if x["status"]=="CLOSED_QUOTE_SIMULATION_ONLY"]
        pos=sum(max(0,r) for r in valid)
        neg=-sum(min(0,r) for r in valid)
        cohorts.append({
            "symbol":sym,"method":method,"side":side,"regime":regime,
            "sampled":len(xs),"quote_closed":len(valid),
            "unverifiable":len(xs)-len(valid),
            "unverifiable_reasons":dict(Counter(x["status"] for x in xs
                if x["status"]!="CLOSED_QUOTE_SIMULATION_ONLY")),
            "mean_assumed_net_r":round(mean(valid),6) if valid else None,
            "profit_factor_assumed":round(pos/neg,5) if neg else None,
            "valid_quote_fraction":round(len(valid)/len(xs),4),
            "validated_live_edge":False,
        })
    # Ex-post diagnosis only; never feed these retrospective labels back
    # into the prospective observer as "independent forward" experience.
    from datetime import datetime,timezone
    methods=defaultdict(list);months=defaultdict(list);monthly_by_method=defaultdict(list)
    for row in rows:
        s=row["signal"];o=row["outcome"]
        methods[(s["method"],s["side"])].append(o)
        month=datetime.fromtimestamp(s["signal_at"],timezone.utc).strftime("%Y-%m")
        months[month].append(o)
        monthly_by_method[(month,s["symbol"],s["method"],s["side"])].append(o)

    def describe(cases):
        values=[x["net_assumed_cost_r"] for x in cases
                if x["status"]=="CLOSED_QUOTE_SIMULATION_ONLY"]
        profits=sum(max(0.,v) for v in values)
        losses=-sum(min(0.,v) for v in values)
        closed=[x for x in cases if x["status"]=="CLOSED_QUOTE_SIMULATION_ONLY"]
        return {
            "sampled":len(cases),"verified_bidask_quote_paths":len(values),
            "not_replayable":len(cases)-len(values),
            "failure_breakdown":dict(Counter(x["status"] for x in cases)),
            "exit_breakdown":dict(Counter(x["exit_reason"] for x in closed)),
            "mean_assumed_net_r":round(mean(values),6) if values else None,
            "profit_factor_assumed":round(profits/losses,5) if losses else None,
            "negative_results":sum(v<0 for v in values),
            "positive_results":sum(v>0 for v in values),
            "quote_coverage":round(len(values)/len(cases),4) if cases else 0.,
            # Diagnostic caution, NOT an adaptive production rule.
            "research_caution":(len(values)>=6 and
                                mean(values)<-.10) if values else False,
            "authorizes_live_or_paper_promotion":False,
        }
    method_scorecard=[
        {"method":method,"side":side,**describe(cases)}
        for (method,side),cases in sorted(methods.items())
    ]
    monthly_scorecard=[
        {"month":month,**describe(cases)}
        for month,cases in sorted(months.items())
    ]
    monthly_symbol_method_scorecard=[
        {"month":month,"symbol":symbol,"method":method,"side":side,
         **describe(cases)}
        for (month,symbol,method,side),cases in sorted(monthly_by_method.items())
    ]
    return {
        "kind":"NONEXECUTED_BROKER_BID_ASK_TICK_PATH_RECONCILIATION",
        "n_sampled":len(rows),
        "quote_completed":sum(x["outcome"]["status"]=="CLOSED_QUOTE_SIMULATION_ONLY"
                              for x in rows),
        "reason_counts":dict(Counter(x["outcome"]["status"] for x in rows)),
        "cohorts":cohorts,
        "method_scorecard":method_scorecard,
        "monthly_scorecard":monthly_scorecard,
        "monthly_symbol_method_scorecard":monthly_symbol_method_scorecard,
        "this_is_ex_post_diagnosis_not_auto_strategy_training":True,
        "full_broker_commission_verified":False,
        "historical_DST_multi_months_verified":False,
        "live_execution_authorized":False
    }
