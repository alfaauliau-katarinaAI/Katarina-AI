"""Audit whether full-M5 V5 portfolio entries agree with old explainable Brain.

Point-in-time features from CLOSED bars only, at selected historical entry
cut. This is a diagnostic *after* V5 selection; not a new OOS trading result.
No trading; news verified=True is an explicit technical counterfactual only.
"""
from __future__ import annotations
import csv,json,time,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_explainable_55_pairs import OUT,get_bars,TIMEFRAME,sensors,bisected_indices,stats
from katarina.intelligence.market_decision_pipeline import MarketDecisionPipeline
TARGET=OUT/"intraday_scalp_full_m5_v5"
def main():
    full=list(csv.DictReader((TARGET/"COMBINED_POLICY_TRADES.csv").open(encoding="utf-8")))
    groups=defaultdict(list)
    for tr in full:
        tr["cut"]=int(tr["cut"]);tr["R"]=float(tr["R"])
        groups[tr["symbol"]].append(tr)
    if not mt5.initialize():raise RuntimeError("MT5_unavailable")
    if mt5.terminal_info().trade_allowed:
        mt5.shutdown();raise RuntimeError("refuse_live_enabled")
    pipeline=MarketDecisionPipeline()
    counters=Counter();logs=[];t0=time.perf_counter()
    for n,(symbol,ts) in enumerate(sorted(groups.items())):
        mt5.symbol_select(symbol,True)
        point=float(mt5.symbol_info(symbol).point)
        raw={}
        for tf,(timeframe,sec,count) in TIMEFRAME.items():
            a=get_bars(symbol,timeframe,count)
            if a is None:raise RuntimeError("missing_frame_"+symbol+"_"+tf)
            raw[tf]=(a,sec,a["time"].astype(np.int64))
        for trade in ts:
            cut=trade["cut"];frames={}
            for tf,(a,sec,times) in raw.items():
                end=bisected_indices(times,cut,sec)
                if end<90 or end>len(a) or int(times[end-1])+sec>cut:
                    counters["missing_closed_context"]+=1;break
                frames[tf]=sensors(a[end-90:end],sec)
            if len(frames)!=3:continue
            a,sec,times=raw["M5"]
            i=int(np.searchsorted(times,cut-300,side="left"))
            if i>=len(times) or int(times[i])!=cut-300:
                counters["missing_signal_m5"]+=1;continue
            spread=float(a["spread"][i])*point
            if spread<=0:continue
            obs=pipeline.evaluate(symbol=symbol,candles=frames,
                as_of_utc=datetime.fromtimestamp(cut,timezone.utc),
                actual_spread=spread,broker_session_open=True,
                data_fresh=True,news_blackout=False,
                news_context_verified=True,
                instrument_point=point)
            agree=(obs.action==trade["side"])
            quality=bool(obs.entry_quality and obs.entry_quality.eligible)
            semantic=bool(obs.semantic_setup and obs.semantic_setup.pattern_confirmed)
            counters["evaluated"]+=1
            counters["brain_side_agree"]+=agree
            counters["brain_entry_quality_agree"]+=quality
            counters["brain_semantics_agree"]+=semantic
            counters["strict_full_agree"]+=(agree and quality and semantic)
            logs.append(dict(symbol=symbol,cut=cut,mode=trade["mode"],
                side=trade["side"],R=trade["R"],score=float(trade["score"]),
                brain_action=obs.action,brain_playbook=obs.playbook,
                side_agree=agree,quality=quality,semantic=semantic,
                full_agree=agree and quality and semantic))
        print("CHECK",n+1,"/",len(groups),symbol,
              "selected",len(ts),"elapsed",round(time.perf_counter()-t0,1),flush=True)
    mt5.shutdown()
    by_group={}
    for mode in ("INTRADAY","SCALP_EXTREME"):
        v=[x for x in logs if x["mode"]==mode]
        yes=[x for x in v if x["full_agree"]]
        by_group[mode]=dict(entries=len(v),all_brain_checks_pass=len(yes),
           aligned_subset_stats=stats(yes))
    report=dict(kind="BRAIN_POINT_IN_TIME_POST_SELECTION_AUDIT",
        limitation="Legacy Brain match checked after independently preselected V5 winners; does not reconstruct a policy that would switch to 2nd-best asset in a checkpoint",
        future_outcome_used_to_select=False,
        historical_news_clear_assumed=True,
        original_selected=len(full),audited=len(logs),
        counters=dict(counters),by_mode=by_group,
        note="Pass rate does not mean validated profit or calibrated AI model",
        orders_sent=0,live_execution_authorized=False)
    (TARGET/"BRAIN_AGREEMENT_AUDIT.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    with (TARGET/"brain_agreement_entries.csv").open("w",newline="",encoding="utf-8") as f:
        if logs:
            w=csv.DictWriter(f,fieldnames=list(logs[0]));w.writeheader();w.writerows(logs)
    print("FINAL_BRAIN_AUDIT",json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__":main()