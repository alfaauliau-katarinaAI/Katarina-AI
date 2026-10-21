"""Forensic causes of prior (already-inspected) native Brain entry failures.

All labels come from frozen pre-entry cards and FUTURE M5 bars ONLY FOR
POST-HOC REVIEW. No trading policy is trained, selected, deployed, or tuned
by this module; the output is an explanation, not prospective evidence.
A target/stop in one M5 candle is an unknowable BID/ASK intrabar order:
conservative stop-first is preserved and ambiguity counted explicitly.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from datetime import datetime,timezone
from math import isfinite
from statistics import mean,median
from typing import Mapping,Sequence

from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle

COST_STRESS_R=.15
EARLY_STOP_SECONDS=15*60


def _ratio(a,b):
    return round(a/b,6) if b and b>0 else None


def _clock(bar):
    dt=bar.closed_at_utc
    if not isinstance(dt,datetime) or dt.tzinfo is None:
        raise ValueError("naive_closed_bar_not_replayable")
    return int(dt.astimezone(timezone.utc).timestamp())


def _one(signal, rows, index):
    stamp=signal["signal_at"]
    if stamp not in index or signal["side"] not in ("BUY","SELL"):
        raise ValueError("unmatched_historical_signal")
    i=index[stamp]
    if i+1>=len(rows):
        raise ValueError("missing_replay_entry_bar")
    side=signal["side"]
    buy=side=="BUY"
    spread=signal["observed_spread_price"]
    entry_bid=rows[i+1].open
    entry=entry_bid+spread if buy else entry_bid
    sl=signal["sl"];tp=signal["tp"]
    risk=entry-sl if buy else sl-entry
    if not all(isfinite(float(v)) for v in
               (spread,entry,sl,tp,risk,signal["proxy_gross_r"])):
        raise ValueError("nonfinite_historical_signal_geometry")
    if risk<=0:raise ValueError("nonpositive_entry_risk")
    end=signal["label_known_at"]
    if end<=stamp:raise ValueError("label_not_in_future_of_signal")
    if end>_clock(rows[min(i+24,len(rows)-1)]):
        raise ValueError("label_beyond_observed_horizon")
    observed=[]
    previous=stamp
    both_hit=False
    stopped=False
    tp_touched=False
    max_favorable=0.
    max_adverse=0.
    observed_minutes=0
    for bar in rows[i+1:]:
        t=_clock(bar)
        if t>end:break
        if t-previous!=300:raise ValueError("unpriced_gap_in_labeled_path")
        previous=t
        low=bar.low if buy else bar.low+spread
        high=bar.high if buy else bar.high+spread
        stop_in_bar=(low<=sl if buy else high>=sl)
        tp_in_bar=(high>=tp if buy else low<=tp)
        both_hit=both_hit or (stop_in_bar and tp_in_bar)
        stopped=stopped or stop_in_bar
        tp_touched=tp_touched or tp_in_bar
        # These are FULL BAR extrema, including possibly prices after
        # the stop/target. Not chronological realized excursions.
        fav=max(0.,high-entry) if buy else max(0.,entry-low)
        adverse=max(0.,entry-low) if buy else max(0.,high-entry)
        max_favorable=max(max_favorable,fav)
        max_adverse=max(max_adverse,adverse)
        observed_minutes+=5
        observed.append(t)
    if not observed or observed[-1]!=end:
        raise ValueError("exit_label_not_at_broker_M5_close")
    outcome=signal["proxy_exit_reason"]
    if outcome.startswith("TARGET") and (not tp_touched or both_hit):
        raise ValueError("target_label_conflicts_with_stop_first")
    if outcome.startswith("STOP") and not stopped:
        raise ValueError("stop_label_without_touch")
    if outcome.startswith("TIMESTOP") and (stopped or tp_touched):
        raise ValueError("time_exit_contains_prior_stop_or_target")
    net=float(signal["proxy_gross_r"])-COST_STRESS_R
    return {
        "symbol":signal["symbol"],
        "method":signal["method"],"side":side,"regime":signal["regime"],
        "signal_epoch":stamp,"exit_epoch":end,
        "signal_month":datetime.fromtimestamp(stamp,timezone.utc).strftime("%Y-%m"),
        "exit_reason":("STOP" if outcome.startswith("STOP") else
                       "TARGET" if outcome.startswith("TARGET") else "TIME"),
        "gross_proxy_r":signal["proxy_gross_r"],
        "net_proxy_r_assuming_0_15_extra_cost":round(net,7),
        "is_loss":net<0,
        "holding_minutes":observed_minutes,
        "early_stop_first_15m":(outcome.startswith("STOP") and
                                end-stamp<=EARLY_STOP_SECONDS),
        "both_stop_target_inside_one_M5_bar":both_hit,
        "pre_entry_spread_over_stop_risk":_ratio(spread,risk),
        "stop_distance_over_pre_entry_m15_atr":_ratio(
            risk,signal.get("m15_atr_price")),
        "after_entry_unsequenced_M5_max_favorable_r":_ratio(max_favorable,risk),
        "after_entry_unsequenced_M5_max_adverse_r":_ratio(max_adverse,risk),
        "directional_alignment":signal.get("directional_alignment","UNASSESSED"),
        "next_open_ask_spread_ASSUMED_to_equal_signal_spread":True,
        "future_M5_extrema_NOT_reliable_intrabar_fill_order":True,
        "no_broker_orders":True,
    }


def _summarize(trades):
    values=[r["net_proxy_r_assuming_0_15_extra_cost"] for r in trades]
    positives=sum(max(0,v) for v in values)
    negatives=-sum(min(0,v) for v in values)
    losses=[t for t in trades if t["is_loss"]]
    reasons=Counter(t["exit_reason"] for t in trades)
    loss_reasons=Counter(t["exit_reason"] for t in losses)
    def val(field):
        a=[x[field] for x in trades if x[field] is not None]
        return round(median(a),5) if a else None
    return {
        "n":len(trades),
        "profitable_after_assumed_cost":len(trades)-len(losses),
        "losses_after_assumed_cost":len(losses),
        "mean_net_proxy_r":round(mean(values),6) if values else None,
        "profit_factor_proxy":round(positives/negatives,6) if negatives else None,
        "exit_causes":dict(reasons),
        "loss_exit_causes":dict(loss_reasons),
        "ambiguous_intrabar_stop_vs_target_count":sum(
            t["both_stop_target_inside_one_M5_bar"] for t in trades),
        "early_stop_within_15m_count":sum(t["early_stop_first_15m"] for t in trades),
        "median_holding_minutes":val("holding_minutes"),
        "median_pre_entry_spread_to_risk":val("pre_entry_spread_over_stop_risk"),
        "median_stop_distance_to_M15_atr":val(
            "stop_distance_over_pre_entry_m15_atr"),
        "median_fullbar_max_favorable_r_not_realized":val(
            "after_entry_unsequenced_M5_max_favorable_r"),
        "median_fullbar_max_adverse_r_not_realized":val(
            "after_entry_unsequenced_M5_max_adverse_r"),
        "research_can_promote_this_automatically":False,
    }


def diagnose_frozen_replay(result,frames:Mapping[str,Mapping[str,Sequence[SensorCandle]]]):
    """Full coverage of every labeled signal. No winners-only filtering."""
    signals=result["signals"]
    candles={}
    indices={}
    for symbol,bars in frames.items():
        series=bars["M5"]
        rows={_clock(b):i for i,b in enumerate(series)}
        if len(rows)!=len(series):
            raise ValueError("duplicate_hist_time")
        candles[symbol]=series
        indices[symbol]=rows
    all_details=[]
    for sig in signals:
        sym=sig["symbol"]
        if sym not in candles:raise ValueError("no_source_broker_history")
        all_details.append(_one(sig,candles[sym],indices[sym]))
    groups=defaultdict(list)
    months=defaultdict(list)
    symbols=defaultdict(list)
    for row in all_details:
        groups[(row["method"],row["side"])].append(row)
        months[row["signal_month"]].append(row)
        symbols[row["symbol"]].append(row)
    totals=_summarize(all_details)
    totals["research_proposals_frozen_before_outcome"]=len(
        result["all_technical_proposals"])
    totals["OHLC_proxy_labels_completed"]=len(all_details)
    totals["censored_or_gap_proxy_labels"]=result["counters"].get(
        "quote_path_unavailable",0)
    totals["no_technical_entry_count"]=result["counters"].get(
        "technical_wait",0)
    totals["entry_geometry_rejected_count"]=result["counters"].get(
        "invalid_rr_or_stop",0)
    totals["missing_historical_signal_spread_count"]=result["counters"].get(
        "spread_unavailable",0)
    totals["technical_evaluations"]=result["counters"].get("evaluated",0)
    return {
        "purpose":"EX_POST_ROOT_CAUSE_INSPECTED_OHLC_PROXY_NOT_TICK_FILLS",
        "sample_provenance":"BROKER_M5_OHLC_SIGNAL_CLOSE_SPREAD",
        "counterfactual_entry_rules_not_optimized_here":True,
        "same_bar_stop_target_order_UNKNOWABLE":True,
        "totals":totals,
        "by_method_side":[{"method":k[0],"side":k[1],**_summarize(rows)}
                          for k,rows in sorted(groups.items())],
        "by_month":[{"month":month,**_summarize(rows)}
                    for month,rows in sorted(months.items())],
        "by_symbol":[{"symbol":sym,**_summarize(rows)}
                     for sym,rows in sorted(symbols.items())],
        "all_candidate_records":all_details,
        "no_live_or_paper_policy_promotion":True,
        "orders_sent":0,"live_execution_authorized":False,
    }
