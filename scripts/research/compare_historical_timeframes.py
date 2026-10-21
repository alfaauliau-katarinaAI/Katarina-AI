"""Compare M1/M5 research costs on the same dates, never select a winner."""
from __future__ import annotations
import argparse,json
from math import isfinite
from pathlib import Path
from statistics import mean

def compare(m1,m5):
    if m1.get("report_version")!="historical_tick_shadow_v1":
        raise ValueError("invalid_m1_report")
    if m5.get("report_version")!="historical_m5_m15_shadow_v1":
        raise ValueError("invalid_m5_report")
    if m1["period"]!=m5["period"]:
        raise ValueError("non_matching_calendar_windows")
    if m1.get("live_execution_enabled") is not False or m5.get("live_execution_enabled") is not False:
        raise ValueError("cannot_compare_live_results")
    # Exact common universe, including disabled broker symbols, avoids
    # data snooping on newly discovered profitable securities.
    one={x["symbol"] for x in m1["symbols"]}
    five={x["symbol"] for x in m5["symbols"]}
    if one!=five:
        raise ValueError("unmatched_symbol_universe")
    by_tf={}
    for name,report in (("M1_M5",m1),("M5_M15",m5)):
        signals=[s for rec in report["symbols"] for s in rec.get("signals",[])]
        if len(signals)!=report["signals_observed"]:
            raise ValueError("inconsistent_signal_counts")
        if any((not isfinite(float(s["entry_spread_atr"])) or
                not isfinite(float(s["quoted_markout_bps"])) or
                bool(s["cost_screen_pass"])!=(float(s["entry_spread_atr"])<=.15))
                for s in signals):
            raise ValueError("malformed_cost_evidence")
        costs=[s for s in signals if s["cost_screen_pass"]]
        by_side={}
        for side in ("BUY","SELL"):
            arr=[s["quoted_markout_bps"] for s in costs if s["side"]==side]
            by_side[side]=dict(n=len(arr),mean_quoted_markout_bps=mean(arr) if arr else None,
                 positive_fraction=sum(x>0 for x in arr)/len(arr) if arr else None)
        by_tf[name]=dict(technical_hypotheses=len(signals),
            spread_qualified=len(costs),cost_pass_fraction=len(costs)/len(signals) if signals else None,
            spread_qualified_by_side=by_side,
            available_symbols_with_bar_history=sum(1 for rec in report["symbols"]
                  if rec.get("m1_bars_available" if name=="M1_M5" else "m5_bars_available",0)>0))
    return dict(kind="timeframe_cost_feasibility_comparison",
        period=m1["period"],symbol_count=len(one),timeframe_profiles=by_tf,
        different_signal_populations=True,
        m1_vs_m5_atr_denominators_are_not_comparable=True,
        explanation="Do not rank these as trading strategies. Entries, trend contexts, and ATR denominators differ.",
        historical_macro_vintages_missing=True,
        stop_loss_take_profit_paths_tested=False,
        fees_and_slippage_calibrated=False,
        model_promotion_allowed=False,live_execution_enabled=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--m1-report",required=True)
    p.add_argument("--m5-report",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    one=json.loads(Path(a.m1_report).read_text(encoding="utf-8"))
    five=json.loads(Path(a.m5_report).read_text(encoding="utf-8"))
    result=compare(one,five)
    path=Path(a.output)
    if path.exists():raise FileExistsError("immutable_comparison_exists")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(result["timeframe_profiles"],indent=2))
    print("REPORT "+str(path))
if __name__=="__main__":
    main()
