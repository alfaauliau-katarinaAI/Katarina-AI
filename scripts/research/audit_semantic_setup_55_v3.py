"""All-pair semantic setup falsification under baseline-identical trade outcomes.

Strictly CLOSED point-in-time candles before the sampled signal.
Research-only, no new signals, no execution and no claim of independent OOS.
"""
from __future__ import annotations
import csv,json,sys,time
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_explainable_55_pairs import OUT,get_bars,sensors,bisected_indices,stats,split,TIMEFRAME
from katarina.intelligence.perception.structural_entry_quality import StructuralEntryQuality
from katarina.intelligence.perception.semantic_setup_truth import CausalSetupValidator

DEST=OUT/"semantic_v3_full_55"
DEST.mkdir(parents=True,exist_ok=True)
def main():
    if not mt5.initialize():raise RuntimeError("MT5 initialization failed")
    if mt5.terminal_info().trade_allowed:
        mt5.shutdown();raise RuntimeError("Trading enabled; refusing research replay")
    entry=StructuralEntryQuality()
    semantic=CausalSetupValidator()
    kept={"baseline":[],"v1_gate":[],"semantic_only":[],"both":[]}
    per_pair=[];fails=[];reasons=Counter();by_playbook=defaultdict(lambda:Counter())
    start=time.perf_counter()
    paths=sorted(OUT.glob("*_vx.json"))
    for k,path in enumerate(paths):
        source=json.loads(path.read_text(encoding="utf-8"))
        sym=source["symbol"];original=source["events"]
        local={"baseline":list(original),"v1_gate":[],"semantic_only":[],"both":[]}
        mistakes=Counter()
        if original:
            mt5.symbol_select(sym,True)
            info=mt5.symbol_info(sym)
            if info is None:
                fails.append(dict(symbol=sym,error="symbol_info_missing"));continue
            point=float(info.point)
            market={}
            for tf,(code,period,n) in TIMEFRAME.items():
                a=get_bars(sym,code,n)
                if a is None:
                    fails.append(dict(symbol=sym,error="history_missing_"+tf));break
                market[tf]=(a,period,a["time"].astype(np.int64))
            if len(market)!=3:continue
            for old in original:
                when=int(old["entry_time"])
                parts={}
                for tf,(a,sec,times) in market.items():
                    end=bisected_indices(times,when,sec)
                    if end<55 or end>len(a):
                        mistakes["history_short_"+tf]+=1;break
                    if int(times[end-1])+sec>when:
                        raise AssertionError("future candle at signal")
                    parts[tf]=sensors(a[end-55:end],sec)
                if len(parts)!=3:continue
                a,sec,times=market["M5"]
                last=int(np.searchsorted(times,when-300,side="left"))
                if last>=len(a) or int(times[last])!=when-300:
                    mistakes["no_M5_matching_signal_bar"]+=1;continue
                spread=float(a["spread"][last])*point
                if spread<=0:mistakes["spread_missing"]+=1;continue
                timeutc=datetime.fromtimestamp(when,timezone.utc)
                try:
                    q=entry.assess(side=old["side"],playbook=old["playbook"],
                        m5=parts["M5"],m15=parts["M15"],h1=parts["H1"],
                        spread=spread,as_of_utc=timeutc)
                    s=semantic.assess(side=old["side"],playbook=old["playbook"],
                        m5=parts["M5"],m15=parts["M15"],h1=parts["H1"],
                        spread=spread,as_of_utc=timeutc)
                except ValueError:
                    mistakes["value_error"]+=1;continue
                if q.eligible:local["v1_gate"].append(old)
                if s.pattern_confirmed:local["semantic_only"].append(old)
                if s.pattern_confirmed and q.eligible:local["both"].append(old)
                else:
                    reasons.update(s.blockers)
                by_playbook[old["playbook"]]["original"]+=1
                if s.pattern_confirmed:by_playbook[old["playbook"]]["true_semantic"]+=1
                if s.pattern_confirmed and q.eligible:
                    by_playbook[old["playbook"]]["both"]+=1
        for key in kept:kept[key].extend(local[key])
        per_pair.append(dict(symbol=sym,original=len(local["baseline"]),
            v1_count=len(local["v1_gate"]),semantic_count=len(local["semantic_only"]),
            combined_count=len(local["both"]),
            original_mean_R=stats(local["baseline"])["avg_R"],
            v1_mean_R=stats(local["v1_gate"])["avg_R"],
            semantic_mean_R=stats(local["semantic_only"])["avg_R"],
            combined_mean_R=stats(local["both"])["avg_R"],
            combined_PF=stats(local["both"])["PF"],
            combined_stress_0_1_mean_R=round(
                stats(local["both"])["avg_R"]-.1,5)
                if local["both"] else None,
            combined_2025_mean_R=stats([x for x in local["both"]
                if split(x["entry_time"])=="2025_available"])["avg_R"],
            combined_2026_Jan_May_mean_R=stats([x for x in local["both"]
                if split(x["entry_time"])=="2026_Jan_May"])["avg_R"],
            combined_2026_Jun_Oct_mean_R=stats([x for x in local["both"]
                if split(x["entry_time"])=="2026_Jun_Oct"])["avg_R"],
            invalid_source=sum(mistakes.values())))
        if mistakes:fails.append(dict(symbol=sym,count=dict(mistakes)))
        print("PAIR",k+1,"/",len(paths),sym,"initial",len(original),
            "semantic",len(local["semantic_only"]),"combined",len(local["both"]),
            "combined_mean",stats(local["both"])["avg_R"],flush=True)
    mt5.shutdown()
    for events in kept.values():
        events.sort(key=lambda x:(x["exit_time"],x["symbol"]))
    summary=dict(kind="SEMANTIC_SETUP_FALSIFICATION_FULL_55",
      symbols=len(paths),compared=len(per_pair),errors=fails,
      assumption="Identical historical signals, next-bar entry, costs, ATR SL and 1.8R TP",
      historical_news_verified=False,independent_oos=False,
      every_nth_M5_bar=36,live_execution_authorized=False,orders_sent=0,
      totals={key:stats(vals) for key,vals in kept.items()},
      periods={label:{key:stats([x for x in vals if split(x["entry_time"])==label])
                    for key,vals in kept.items()}
        for label in ("2025_available","2026_Jan_May","2026_Jun_Oct")},
      strategies=dict(by_playbook),rejections=dict(reasons),
      per_pair=per_pair,seconds=round(time.perf_counter()-start,1))
    (DEST/"RESULT.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    with (DEST/"per_pair.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(per_pair[0]));w.writeheader();w.writerows(per_pair)
    print("FINAL",json.dumps({k:summary[k] for k in ("symbols","compared","errors","totals","periods","strategies","seconds")},ensure_ascii=False),flush=True)
if __name__=="__main__":main()