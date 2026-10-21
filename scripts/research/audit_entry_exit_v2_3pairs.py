"""Read-only paired Entry/Exit V2 audit across XAUUSD, EURUSD and US30.

Same historical M5 signals as original 55-pair sampled replay.
- baseline: recorded original fixed ATR exits
- gate-only: structural entry filter retaining original exits
- gate+exit: structural invalidation & prior CLOSED M15/H1 level target
No intrabar claims; stop-first, approximate bar spread, extra 0.03R cost.
2025/2026 history has ALREADY been viewed, NOT independent holdout.
"""
from __future__ import annotations
import csv, json, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_explainable_55_pairs import (
    OUT, TIMEFRAME, get_bars, sensors, bisected_indices, stats, split,
)
from katarina.intelligence.structural_entry_quality import StructuralEntryQuality
from katarina.intelligence.structure_exit_plan import StructuralExitPlanner

SYMBOLS=("XAUUSD.vx","EURUSD.vx","US30.vx")
DEST=OUT/"entry_exit_v2_diagnostic_3_pairs"
DEST.mkdir(parents=True,exist_ok=True)
HOLD=36
EXTRA_COST_R=.03
SLIP_POINTS=1.

def settle(arr,i,side,stop,target,point):
    """Next M5 bar fill, adverse one-point slippage; M5 Bid OHLC.

    SELL exits evaluated at approximate ask=bid+per-bar broker spread.
    Ambiguous SL+TP bar => SL first; stops gap-through at adverse open.
    """
    if i+HOLD>=len(arr):return None
    if int(arr["time"][i+1])-int(arr["time"][i])!=300:return None
    b=arr[i+1]
    spr=int(b["spread"])*point
    if spr<=0:return None
    entry=float(b["open"])+(spr if side==1 else 0)+side*SLIP_POINTS*point
    risk=side*(entry-stop)
    reward=side*(target-entry)
    if risk<=max(2*spr,4*point) or reward/risk<1.25:return None
    endidx=i
    kind="TIME";mark=entry
    mfe=0.;mae=0.
    for j in range(i+1,i+HOLD+1):
        if j>i+1 and int(arr["time"][j])-int(arr["time"][j-1])!=300:break
        x=arr[j]
        ask_spread=max(0,int(x["spread"]))*point
        high=float(x["high"])+(ask_spread if side<0 else 0.)
        low=float(x["low"])+(ask_spread if side<0 else 0.)
        open_=float(x["open"])+(ask_spread if side<0 else 0.)
        mfe=max(mfe,side*(high-entry) if side==1 else side*(low-entry))
        mae=max(mae,side*(entry-low) if side==1 else side*(entry-high))
        slhit=low<=stop if side==1 else high>=stop
        tphit=high>=target if side==1 else low<=target
        if slhit:
            mark=(min(open_,stop) if side==1 else max(open_,stop))-side*SLIP_POINTS*point
            kind="SL"
        elif tphit:
            mark=target-side*SLIP_POINTS*point
            kind="TP"
        else:
            mark=float(x["close"])+(ask_spread if side<0 else 0.)-side*SLIP_POINTS*point
        endidx=j
        if slhit or tphit:break
    if endidx==i:return None
    return dict(R=round(side*(mark-entry)/risk-EXTRA_COST_R,7),
                outcome=kind, entry_time=int(arr["time"][i+1]),
                exit_time=int(arr["time"][endidx])+300,
                hold_bars=endidx-i, mfe_r=round(mfe/risk,3),
                mae_r=round(mae/risk,3),entry=round(entry,8),
                stop=round(stop,8),target=round(target,8),
                initial_rr=round(reward/risk,3))

def post_sl_recovery(arr, event, risk):
    """Diagnostic only, uses FUTURE bars, MUST NOT be an entry feature."""
    if event["result"]!="SL":return None
    entry_time=int(event["entry_time"])
    stop_time=int(event["exit_time"])
    idx=int(np.searchsorted(arr["time"],entry_time,side="left"))
    j=int(np.searchsorted(arr["time"],stop_time,side="left"))
    if idx>=len(arr) or j>=len(arr):return None
    side=1 if event["side"]=="BUY" else -1
    spread=max(0,int(arr["spread"][idx]))*risk[1]
    entry=float(arr["open"][idx])+(spread if side>0 else 0)
    favourable=False
    adverse=False
    for k in range(j,min(j+24,len(arr))):
        if k>j and int(arr["time"][k])-int(arr["time"][k-1])!=300:break
        close=float(arr["close"][k])
        if side*(close-entry)>=risk[0]:
            favourable=True;break
        if side*(close-entry)<=-2*risk[0]:
            adverse=True;break
    return "recovered_1R_after_SL" if favourable else (
        "adverse_2R_after_SL" if adverse else "no_1R_recovery_next_24_M5")

def main():
    if not mt5.initialize():raise RuntimeError("MT5 connection unavailable")
    terminal=mt5.terminal_info()
    if terminal is None or terminal.trade_allowed:
        mt5.shutdown()
        raise RuntimeError("refuse replay: MT5 trading must be disabled")
    entry=StructuralEntryQuality()
    exit_plan=StructuralExitPlanner()
    reports={}
    all_baseline=[];all_gate=[];all_exit=[]
    start=time.perf_counter()
    for symbol in SYMBOLS:
        mt5.symbol_select(symbol,True)
        info=mt5.symbol_info(symbol)
        point=float(info.point)
        prev=json.loads((OUT/(symbol.replace(".","_")+".json")).read_text(encoding="utf-8"))
        original=prev["events"]
        market={}
        for key,(tf,sec,n) in TIMEFRAME.items():
            arr=get_bars(symbol,tf,n)
            if arr is None:raise RuntimeError("missing MT5 historical "+symbol+" "+key)
            market[key]=(arr,sec)
        arr=market["M5"][0]
        clock={k:v[0]["time"].astype(np.int64) for k,v in market.items()}
        baseline=sorted(original,key=lambda x:x["exit_time"])
        gate=[];adaptive=[];gate_counts=Counter();diagnostics=Counter()
        stops=Counter();sl_lives=[];models=[]
        for n,trade in enumerate(original):
            cut=int(trade["entry_time"])
            nextidx=int(np.searchsorted(clock["M5"],cut,side="left"))
            signalidx=nextidx-1
            if nextidx>=len(arr) or signalidx<60 or int(arr["time"][signalidx])!=cut-300:
                gate_counts["unmatched_original_signal"]+=1;continue
            # Close-time aligns with entry/open time, no right-edge peeking.
            frames={}
            for tf,(bars,sec) in market.items():
                end=bisected_indices(clock[tf],cut,sec)
                if end<55:
                    gate_counts["insufficient_closed_history_"+tf]+=1;break
                raw=bars[end-55:end]
                if int(raw[-1]["time"])+sec>cut:raise AssertionError("future_candle")
                frames[tf]=sensors(raw,sec)
            if len(frames)!=3:continue
            prior=frames["M5"]
            spread=float(arr["spread"][signalidx])*point
            if spread<=0:
                gate_counts["invalid_signal_spread"]+=1;continue
            side_num=1 if trade["side"]=="BUY" else -1
            # Diagnostic: losing trade adverse selection vs stop placement.
            recent_tr=[
                max(arr["high"][k]-arr["low"][k],
                    abs(arr["high"][k]-arr["close"][k-1]),
                    abs(arr["low"][k]-arr["close"][k-1]))
                for k in range(signalidx-13,signalidx+1)
            ]
            atr=float(np.mean(recent_tr))
            if atr>0 and trade["result"]=="SL":
                diagnostics["baseline_stop_loss"]+=1
                stopped_after=(int(trade["exit_time"])-cut)//300
                if stopped_after<=3:diagnostics["baseline_stop_within_3_M5"]+=1
                original_risk=float(trade["risk_price"])
                rec=post_sl_recovery(arr,trade,(original_risk,point))
                if rec:diagnostics[rec]+=1
            q=entry.assess(side=trade["side"],playbook=trade["playbook"],
                m5=frames["M5"],m15=frames["M15"],h1=frames["H1"],
                spread=spread,as_of_utc=datetime.fromtimestamp(cut,timezone.utc))
            if not q.eligible:
                gate_counts.update(q.blockers);continue
            gate.append(trade)
            close=float(prior[-1].close)
            suggested_entry=close+(spread if side_num>0 else 0.)
            proposal=exit_plan.plan(
                side=trade["side"],m5=frames["M5"],
                m15=frames["M15"],h1=frames["H1"],
                expected_entry=suggested_entry,spread=spread,point=point,
                as_of_utc=datetime.fromtimestamp(cut,timezone.utc))
            if not proposal.approved_for_research:
                stops.update(proposal.blockers);continue
            if abs(float(arr["open"][nextidx])-close)>0.5*max(atr,point):
                stops["next_open_gap_gt_0_5_atr"]+=1;continue
            outcome=settle(arr,signalidx,side_num,
                float(proposal.stop),float(proposal.target),point)
            if outcome is None:
                stops["post_fill_rr_or_continuity_reject"]+=1;continue
            outcome.update(symbol=symbol,side=trade["side"],
                regime=trade["regime"],playbook=trade["playbook"],
                stop_basis=proposal.stop_basis,
                target_basis=proposal.target_basis)
            adaptive.append(outcome)
        all_baseline+=baseline
        all_gate+=gate
        all_exit+=adaptive
        reports[symbol]={
            "available_M5_first":datetime.fromtimestamp(int(arr["time"][0]),timezone.utc).isoformat(),
            "available_M5_last":datetime.fromtimestamp(int(arr["time"][-1]),timezone.utc).isoformat(),
            "baseline":stats(baseline),
            "filter_only":stats(gate),
            "structural_entry_exit":stats(adaptive),
            "diagnostics":dict(diagnostics),
            "entry_rejection_counts":dict(gate_counts),
            "exit_rejection_counts":dict(stops),
            "models":adaptive,
            "periods":{
              label:{
                "original":stats([x for x in baseline if split(x["entry_time"])==label]),
                "filter":stats([x for x in gate if split(x["entry_time"])==label]),
                "entry_exit":stats([x for x in adaptive if split(x["entry_time"])==label])
              } for label in ("2025_available","2026_Jan_May","2026_Jun_Oct")
            },
        }
        (DEST/(symbol.replace(".","_")+"_diagnostic.json")).write_text(
            json.dumps(reports[symbol],indent=2,ensure_ascii=False,allow_nan=False),
            encoding="utf-8")
        print("SYMBOL",symbol,"base",len(baseline),"filter",len(gate),
              "adaptive",len(adaptive),
              "avg_R",reports[symbol]["structural_entry_exit"]["avg_R"],
              "diag",dict(diagnostics),flush=True)
    mt5.shutdown()
    for vals in (all_baseline,all_gate,all_exit):
        vals.sort(key=lambda x:(x["exit_time"],x["symbol"]))
    summary={
      "kind":"ENTRY_FAILURE_AUDIT_AND_CAUSAL_BRACKET_EXIT_V2",
      "symbols":SYMBOLS,
      "baseline":stats(all_baseline),
      "filter_only":stats(all_gate),
      "entry_exit_v2":stats(all_exit),
      "periods":{
         p:{"baseline":stats([x for x in all_baseline if split(x["entry_time"])==p]),
            "filter":stats([x for x in all_gate if split(x["entry_time"])==p]),
            "exit_v2":stats([x for x in all_exit if split(x["entry_time"])==p])}
         for p in ("2025_available","2026_Jan_May","2026_Jun_Oct")
      },
      "cost_stress":{
        str(extra):stats([dict(x,R=x["R"]-extra) for x in all_exit])
        for extra in (.1,.2)
      },
      "per_symbol":{k:{n:v[n] for n in ("baseline","filter_only",
                     "structural_entry_exit","diagnostics",
                     "entry_rejection_counts","exit_rejection_counts","periods",
                     "available_M5_first","available_M5_last")} for k,v in reports.items()},
      "no_live_orders":True,"live_authorized":False,
      "independent_out_of_sample":False,
      "historical_news_verified":False,
      "sampling_every_M5_bars":36,
      "exit_time_limit_M5":HOLD,
      "fills":"next M5 open, historical bar spread approximate, one adverse point fill, stop-first ambiguous, 0.03R additional estimated fee",
      "notes":[
        "MT5 server timestamp fields not fully reconciled with broker time zone; within-terminal timeframe alignment only",
        "Historical news assumed clear, but unverified",
        "Price levels from closed candles only, no lookahead in signals or exits",
        "Original entry samples are only 1 in 36 M5 bars, and all historical data have been studied previously",
        "Portfolio concurrent exposure and margin are NOT modeled; total R not account growth",
        "Both 0.03R extra fee and one-point slippage are hypothetical, not calibrated to trade confirmations",
        "Zero/few accepted signals cannot validate profitability",
      ],
      "duration_sec":round(time.perf_counter()-start,1)
    }
    (DEST/"FINAL_3_PAIR_AUDIT.json").write_text(
        json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    rows=[]
    for symbol,v in reports.items():
        rows.append({"symbol":symbol,"baseline_n":v["baseline"]["n"],
                     "baseline_avgR":v["baseline"]["avg_R"],
                     "filtered_n":v["filter_only"]["n"],
                     "filtered_avgR":v["filter_only"]["avg_R"],
                     "structural_exit_n":v["structural_entry_exit"]["n"],
                     "structural_exit_avgR":v["structural_entry_exit"]["avg_R"],
                     "structural_exit_pf":v["structural_entry_exit"]["PF"]})
    with (DEST/"per_pair.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print("FINAL",json.dumps({x:summary[x] for x in ("baseline","filter_only",
                     "entry_exit_v2","periods","cost_stress","duration_sec")},
                     ensure_ascii=False),flush=True)

if __name__=="__main__":main()