"""Predeclared cost-threshold *sensitivity*, not parameter optimization.

Re-evaluates existing closed-candle historical shadow markouts for a fixed
grid of spread/ATR affordability screens. Actual bid/ask round-trip spread is
already charged in quoted_markout_bps. Added bps are hypothetical round-trip
fees/slippage stress, NOT a claim about the broker's actual commission.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from statistics import mean, median

THRESHOLDS = (0.15, 0.25, 0.35, 0.50, 0.75, 1.0, 1.5, 2.0, None)
STRESS_EXTRA_BPS = (0.0, 2.0, 5.0, 10.0)
MIN_EVENTS, MIN_DAYS = 30, 10
EXPECTED_TYPES = {
    "M1_M5": "historical_tick_shadow_v1",
    "M5_M15": "historical_m5_m15_shadow_v1",
}

def stats(events, extra=0.0):
    values=[float(e["quoted_markout_bps"])-extra for e in events]
    days={e["signal_bar_close_utc"][:10] for e in events}
    return dict(
        n=len(events), distinct_utc_days=len(days),
        mean_net_quote_bps=mean(values) if values else None,
        median_net_quote_bps=median(values) if values else None,
        positive_fraction=(sum(x>0 for x in values)/len(values)) if values else None,
        observed_spread_cost_bps_mean=(mean(float(e["midpoint_markout_bps"])
                -float(e["quoted_markout_bps"]) for e in events)
                if values else None),
        extra_roundtrip_cost_bps=extra,
        descriptive_coverage_met=len(events)>=MIN_EVENTS and len(days)>=MIN_DAYS,
        realized_strategy_pnl=False,
        promotion_allowed=False,
    )

def load(paths, kind):
    if kind not in EXPECTED_TYPES:
        raise ValueError("unknown_family")
    records, evidence, windows=[],[],set()
    universe=None
    for path in paths:
        blob=Path(path).read_bytes()
        document=json.loads(blob)
        if document.get("report_version")!=EXPECTED_TYPES[kind]:
            raise ValueError("wrong_input_version")
        if document.get("model_promotion_allowed") is not False or document.get("live_execution_enabled") is not False:
            raise ValueError("live_risk_enabled")
        period=(document["period"]["start"],document["period"]["end_exclusive"])
        if period in windows:
            raise ValueError("duplicate_window")
        windows.add(period)
        names={r["symbol"] for r in document["symbols"]}
        if universe is None:
            universe=names
        if names!=universe:
            raise ValueError("changing_broker_catalogue")
        observed=[s for row in document["symbols"] for s in row.get("signals",[])]
        if len(observed)!=document["signals_observed"]:
            raise ValueError("count_mismatch")
        for s in observed:
            price=(float(s["entry_bid"])+float(s["entry_ask"]))/2
            if price<=0:
                raise ValueError("invalid_price")
            inputs=(s["entry_bid"],s["entry_ask"],s["exit_bid"],s["exit_ask"],
                    s["entry_spread_atr"],s["quoted_markout_bps"],s["midpoint_markout_bps"])
            if not all(isfinite(float(x)) for x in inputs):
                raise ValueError("invalid_quote")
            if s["entry_bid"]>s["entry_ask"] or s["exit_bid"]>s["exit_ask"]:
                raise ValueError("crossed_market")
            if float(s["entry_spread_atr"])<0 or (
                bool(s["cost_screen_pass"]) != (float(s["entry_spread_atr"]) <= 0.15)):
                raise ValueError("gate_inconsistent")
            predicted=((float(s["exit_bid"])-float(s["entry_ask"])) if s["side"]=="BUY"
                       else (float(s["entry_bid"])-float(s["exit_ask"])))
            if abs(float(s["quoted_markout_bps"])-predicted/price*10000)>1e-7:
                raise ValueError("incorrect_bid_ask_markout")
            expected_cost=((float(s["entry_ask"])-float(s["entry_bid"]))+
                           (float(s["exit_ask"])-float(s["exit_bid"])))/2/price*10000
            if abs(float(s["midpoint_markout_bps"])-
                   float(s["quoted_markout_bps"])-expected_cost)>1e-7:
                raise ValueError("spread_cost_decomposition_invalid")
            if s.get("live_risk_authorized") is not False or s.get("is_realized_pnl") is not False:
                raise ValueError("incorrect_risk_flag")
        evidence.extend(observed)
        records.append(dict(
            sha256=sha256(blob).hexdigest(),
            input_path=str(path),period=dict(start=period[0],end_exclusive=period[1]),
            symbols=len(names),quoted_proposals=len(observed)))
    return evidence, records

def analyze(inputs):
    result=dict(kind="cost_gate_counterfactual_NOT_executable_PnL",
      study_type="post_hoc_sensitivity_on_previously_researched_prices",
      gate_metric="actual_entry_bid_ask_spread_divided_by_entry_frame_ATR",
      original_gate=0.15,threshold_grid=list(THRESHOLDS),
      hypothetical_additional_roundtrip_bps=list(STRESS_EXTRA_BPS),
      extra_bps_are_not_known_broker_fees=True,
      commission_unknown=True,slippage_unknown=True,
      SL_TP_order_paths_unavailable=True,
      historical_macro_context_unavailable=True,
      eligibility_on_cost_alone_does_not_authorize_trading=True,
      automatic_gate_change_allowed=False,live_execution_enabled=False,
      model_promotion_allowed=False,
      sample_caveat="Overlapping across symbol markets and historic periods already studied.",
      experiments={})
    for kind,paths in inputs.items():
        events,records=load(paths,kind)
        grid=[]
        symbols=set(e["symbol"] for e in events)
        for threshold in THRESHOLDS:
            chosen=[e for e in events if threshold is None or
                    float(e["entry_spread_atr"])<=threshold]
            partitions={}
            for side in ("BUY","SELL"):
                side_sample=[s for s in chosen if s["side"]==side]
                partitions[side]={str(extra):stats(side_sample,extra)
                                  for extra in STRESS_EXTRA_BPS}
            per_window=[]
            for rec in records:
                start=rec["period"]["start"]
                end=rec["period"]["end_exclusive"]
                slice_=[e for e in chosen if
                        start<=e["signal_bar_close_utc"][:10]<end]
                per_window.append(dict(start=start,end_exclusive=end,
                   measured=len(slice_),mean_bps=stats(slice_)["mean_net_quote_bps"]))
            distinct_symbol_sides=defaultdict(list)
            for e in chosen:
                distinct_symbol_sides[(e["symbol"],e["side"])].append(e)
            # Show all well-observed symbol/sides, never rank by best return.
            per_market=[dict(symbol=symbol,side=side,**stats(vals))
                for (symbol,side),vals in sorted(distinct_symbol_sides.items())
                if len(vals)>=MIN_EVENTS]
            grid.append(dict(
                threshold_spread_div_ATR=threshold,
                samples_after_cost_gate=len(chosen),
                percent_of_candidates=len(chosen)/len(events) if events else None,
                distinct_symbols_with_candidates=len({e["symbol"] for e in chosen}),
                by_side=partitions,by_window=per_window,
                symbol_sides_with_30_samples=per_market))
        result["experiments"][kind]=dict(input_evidence=records,quoted_proposals=len(events),
                                         symbol_count_with_signals=len(symbols),grid=grid)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--m1-report",required=True,nargs="+")
    parser.add_argument("--m5-report",required=True,nargs="+")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    result=analyze({"M1_M5":args.m1_report,"M5_M15":args.m5_report})
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        raise FileExistsError("immutable_sensitivity_report_exists")
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("threshold | M1 quotes | M1 BUY mean bps | M1 SELL mean bps | M5 quotes | M5 BUY mean bps | M5 SELL mean bps")
    one=result["experiments"]["M1_M5"]["grid"]
    five=result["experiments"]["M5_M15"]["grid"]
    for a,b in zip(one,five):
        buya=a["by_side"]["BUY"]["0.0"]["mean_net_quote_bps"]
        sella=a["by_side"]["SELL"]["0.0"]["mean_net_quote_bps"]
        buyb=b["by_side"]["BUY"]["0.0"]["mean_net_quote_bps"]
        sellb=b["by_side"]["SELL"]["0.0"]["mean_net_quote_bps"]
        fmt=lambda x:("NA" if x is None else "{:.3f}".format(x))
        print("{} | {} | {} | {} | {} | {} | {}".format(
            a["threshold_spread_div_ATR"],a["samples_after_cost_gate"],
            fmt(buya),fmt(sella),b["samples_after_cost_gate"],fmt(buyb),fmt(sellb)))
    print("REPORT "+str(path))
if __name__=="__main__":
    main()
