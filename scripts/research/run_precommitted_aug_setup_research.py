"""Read-only Aug-2026 research of three FIXED alternative setups from MT5.

No optimization or write to the canonical observer/market Brain. Uses the
existing broker UTC offset consensus and read-only historical M5/M15/H1
loader; augmented with *selected* true historical BID/ASK tick checks.
All raw private records saved to a single bounded report on the VPS.
"""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import argparse,json,sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))

from run_native_brain_causal_broker_replay import load_from_live_terminal
from katarina.intelligence.lab.precommitted_setup_research import (
    research_alternatives,FROZEN_RULE_VERSION,
)
from katarina.intelligence.broker.broker_scan_universe import resolve_broker_symbols
from katarina.intelligence.lab.causal_tick_reconciliation import (
    tick_reconcile,summarize_tick_reconciliation,
)

FROZEN_START="2026-08-10T00:00:00+00:00"
FROZEN_END="2026-08-21T21:00:00+00:00"
MAX_SYMBOLS=5
MAX_TICK_SAMPLES_PER_SYMBOL=3


def research(args):
    import MetaTrader5 as mt
    names=[x.strip() for x in args.symbols.split(",") if x.strip()]
    if not 3<=len(names)<=MAX_SYMBOLS or len(set(names))!=len(names):
        raise ValueError("three_to_five_distinct_bounded_symbols")
    if not mt.initialize():raise RuntimeError("BROKER_NOT_INITIALIZED")
    try:
        terminal=mt.terminal_info()
        if terminal is None or terminal.trade_allowed:
            raise RuntimeError("BROKER_MUST_HAVE_TRADE_PERMISSION_DISABLED")
        approved=set(resolve_broker_symbols(mt.symbols_get()).symbols)
    finally:mt.shutdown()
    if any(sym not in approved for sym in names):
        raise ValueError("not_a_17_symbol_canonical_market")
    start=datetime.fromisoformat(FROZEN_START)
    end=datetime.fromisoformat(FROZEN_END)
    frames,status,offset,spreads=load_from_live_terminal(
        names,max_cuts=2300,include_spreads=True,window_end_utc=end)
    if len(frames)!=len(names):
        raise RuntimeError("BROKER_AUG_HISTORY_UNAVAILABLE:"+str(status))
    data=research_alternatives(frames,spreads,window_start=start,
        window_end=end,max_cuts_per_symbol=3000)
    # Tick sampling depends solely on PRE-OUTCOME signal timing, never
    # on simulated profit or stop/target results.
    by_symbol={}
    for x in data["all_proposals_frozen_before_future_outcome"]:
        by_symbol.setdefault(x["symbol"],[]).append(x)
    selected=[]
    for sym,xs in sorted(by_symbol.items()):
        xs.sort(key=lambda x:(x["signal_epoch"],x["method"],x["side"]))
        # Exhaustive audit is independent of profit/exit labels; it
        # extends (not replaces) the already published time-only sample.
        if args.audit_all and len(xs)>120:
            raise ValueError("tick_audit_per_symbol_resource_bound_120")
        n=len(xs) if args.audit_all else min(MAX_TICK_SAMPLES_PER_SYMBOL,len(xs))
        chosen=(list(xs) if args.audit_all else
                [xs[i*(len(xs)-1)//max(1,n-1)] for i in range(n)])
        selected.extend(chosen)
    selected.sort(key=lambda x:(x["signal_epoch"],x["symbol"]))
    if not mt.initialize():raise RuntimeError("MT5_TICK_RECHECK_FAILED")
    try:
        terminal=mt.terminal_info()
        if terminal is None or terminal.trade_allowed:
            raise RuntimeError("TICK_READ_REQUIRES_TRADE_DISABLED")
        records=[]
        for sym in names:
            local=[x for x in selected if x["symbol"]==sym]
            if not local:continue
            raw=mt.copy_rates_from_pos(sym,mt.TIMEFRAME_M5,1,22000)
            refs=({int(c["time"]):{k:float(c[k]) for k in
                   ("time","open","high","low","close")} for c in raw}
                  if raw is not None else {})
            symbol_info=mt.symbol_info(sym)
            tick_size=float(getattr(symbol_info,"trade_tick_size",0) or
                            getattr(symbol_info,"point",0) or 0)
            for candidate in local:
                raw_at=int(candidate["signal_epoch"])+offset*3600
                ref=refs.get(raw_at)
                if ref is None:
                    result={"status":"ENTRY_RAW_M5_REFERENCE_MISSING"}
                else:
                    ticks=mt.copy_ticks_range(
                        sym,datetime.fromtimestamp(raw_at,timezone.utc),
                        datetime.fromtimestamp(raw_at+7290,timezone.utc),
                        mt.COPY_TICKS_INFO)
                    if ticks is None:
                        result={"status":"MT5_BIDASK_TICK_HISTORY_UNAVAILABLE"}
                    else:
                        signal={"side":candidate["side"],
                            "signal_at":candidate["signal_epoch"],
                            "sl":candidate["stop"],"tp":candidate["target"]}
                        result=tick_reconcile(signal,ticks,ref,
                            raw_offset_hours=offset,tick_size=tick_size,
                            extra_cost_r=.15)
                records.append({
                    "signal":{"symbol":sym,"method":candidate["method"],
                        "side":candidate["side"],"regime":"PRECOMMITTED_RESEARCH",
                        "signal_at":candidate["signal_epoch"],
                        "technical_score":None},
                    "outcome":result,
                })
    finally:mt.shutdown()
    tick_summary=summarize_tick_reconciliation(records)
    data.update({
        "research_scope":"EARLY_AUGUST_FIXED_ALT_SETUPS_NOT_USED_FOR_RULE_SELECTION",
        "history_broker_current_offset_hours":offset,
        "broker_historical_DST_transition_verified":False,
        "broker_data_coverage":status,
        "tick_audit":tick_summary,
        "tick_audit_selection":("EXHAUSTIVE_FROZEN_PROPOSALS_NO_OUTCOME_RANK"
                                if args.audit_all else
                                "TIME_BALANCED_BEFORE_OUTCOME_BY_SYMBOL"),
        "tick_audit_records":records,
        "actual_account_commission_schedule_verified":False,
        "actual_order_fills_verified":False,
        "historical_period_claimed_pristine_independent_OOS":False,
        "orders_sent":0,"live_execution_authorized":False,
        "read_only":True,
    })
    report=Path(args.output)
    report.parent.mkdir(parents=True,exist_ok=True)
    tmp=report.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
                   encoding="utf-8")
    tmp.replace(report)
    print("FROZEN_AUG_SETUP_BROKER_RESEARCH",json.dumps({
        "symbols":names,
        "rules":FROZEN_RULE_VERSION,
        "evaluated":data["counters"].get("market_clocks",0),
        "proposals":data["technical_proposals"],
        "labels":data["simulated_outcomes"],
        "censored":data["counters"].get("censored_future_or_entry_geometry",0),
        "mean_0_15r":data["all_plus_0_15R_assumed"]["mean_net_assumed_r"],
        "method_sides":[{"method":x["method"],"side":x["side"],
            "n":x["plus_0_15R_assumed"]["n"],
            "mean":x["plus_0_15R_assumed"]["mean_net_assumed_r"]}
            for x in data["by_method_side"]],
        "tick_checks":tick_summary["n_sampled"],
        "tick_valid":tick_summary["quote_completed"],
        "tick_status":tick_summary["reason_counts"],
        "orders":0,"live":False
    },allow_nan=False),flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbols",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--audit-all",action="store_true",
                   help="Read full real broker BID/ASK tick paths for EVERY frozen proposal")
    args=p.parse_args()
    research(args)


if __name__=="__main__":main()
