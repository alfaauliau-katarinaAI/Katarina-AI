"""Time/volatility/spread matched *same direction* control, NAS100 only.

Fixed before viewing output: 4 independently seeded control timestamps
per real-playbook signal, same trading date/session and +/-120 minute UTC,
>=45min away, ATR within 30%, spread/ATR within .12. Stop/target price
distances scaled by the ratio to ATR of the original entry. All quotes
real historical MT5 ticks. This is research, not a valid untouched OOS
test, and never touches broker orders.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from hashlib import sha256
from pathlib import Path
from random import Random
from statistics import mean
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from replay_symbol_playbooks import simulate_structure,tick_series
from historical_shadow_ticks import first_quote,bars
from katarina.intelligence.symbol_playbooks import _ny_open_utc_minutes

UTC=timezone.utc
SYMBOL="NAS100.vx"
SEED=2026101107
CONTROLS_PER_ANCHOR=4
MAX_ATTEMPTS=28
DISTANCE_LIMIT=120*60
MIN_SEPARATION=45*60
ATR_TOLERANCE=.30
COST_RATIO_TOLERANCE=.12
SPREAD_CAP=.35
STRESS_TICKS=1

def when(s):
    return datetime.fromisoformat(s).timestamp()

def atr_at(rows,index):
    if index<14:return None
    trs=[]
    for j in range(index-13,index+1):
        b=rows[j];previous=rows[j-1]
        trs.append(max(b["high"]-b["low"],abs(b["high"]-previous["close"]),
                       abs(b["low"]-previous["close"])))
    return mean(trs)

def pool(rows,anchor_time,anchor_atr):
    candidate=[]
    stamp=int(anchor_time)
    for i in range(15,len(rows)):
        close=rows[i]["time"]+60
        if close<stamp-DISTANCE_LIMIT or close>stamp+DISTANCE_LIMIT:continue
        if abs(close-stamp)<MIN_SEPARATION:continue
        target_dt=datetime.fromtimestamp(close,UTC)
        if target_dt.date()!=datetime.fromtimestamp(stamp,UTC).date():continue
        minute=target_dt.hour*60+target_dt.minute
        if not _ny_open_utc_minutes(target_dt,9,40)<=minute<=_ny_open_utc_minutes(target_dt,15):
            continue
        if rows[i]["time"]-rows[i-14]["time"]>20*60:
            continue
        atr=atr_at(rows,i)
        if atr is None or atr<=0 or abs(atr/anchor_atr-1)>ATR_TOLERANCE:
            continue
        candidate.append((float(close),atr))
    return candidate

def bootstrap_pair(rows,repeats=1000):
    if not rows:return None
    grouped=defaultdict(list)
    for row in rows:
        grouped[row["signal_utc"][:10]].append(row["lift_R"])
    days=sorted(grouped)
    rng=Random(20261011)
    values=[]
    for i in range(repeats):
        keys=(rng.choice(days) for _ in days)
        flat=[v for key in keys for v in grouped[key]]
        values.append(mean(flat))
    values.sort()
    return [values[int(.025*(repeats-1))],values[int(.975*(repeats-1))]]

def run(mt5,anchors):
    if not mt5.symbol_select(SYMBOL,True):
        raise RuntimeError("NAS100_not_authorized")
    info=mt5.symbol_info(SYMBOL)
    # Retrieve independent candles strictly up to Oct10; never interpolates
    # a quote or fills a missing M1 bar with M5 projections.
    windows=((datetime(2026,7,1,tzinfo=UTC),datetime(2026,8,1,tzinfo=UTC)),
             (datetime(2026,8,16,tzinfo=UTC),datetime(2026,9,1,tzinfo=UTC)),
             (datetime(2026,9,15,tzinfo=UTC),datetime(2026,10,1,tzinfo=UTC)),
             (datetime(2026,10,1,tzinfo=UTC),datetime(2026,10,10,tzinfo=UTC)))
    per_window=[]
    for start,end in windows:
        raw=mt5.copy_rates_range(SYMBOL,mt5.TIMEFRAME_M1,
            start-timedelta(days=3),end)
        per_window.append((start.timestamp(),end.timestamp(),bars(raw) if raw is not None else []))
    rng=Random(SEED)
    paired=[]
    counts=Counter()
    for signal in sorted(anchors,key=lambda x:x["quote_entry_utc"]):
        counts["anchors_seen"]+=1
        signal_sec=when(signal["entry_signal_close_utc"])
        window=next((chunk[2] for chunk in per_window
                     if chunk[0]<=signal_sec<chunk[1]),[])
        if not window:
            counts["missing_historical_window"]+=1
            continue
        options=pool(window,signal_sec,signal["signal_atr"])
        rng.shuffle(options)
        if not options:
            counts["no_matched_ATR_time_pool"]+=1
            continue
        anchor_open=(signal["broker_quote_entry_ask"] if signal["side"]=="BUY"
                     else signal["broker_quote_entry_bid"])
        risk=anchor_open-signal["stop_price"] if signal["side"]=="BUY" else (
            signal["stop_price"]-anchor_open)
        reward=signal["target_price"]-anchor_open if signal["side"]=="BUY" else (
            anchor_open-signal["target_price"])
        if risk<=0 or reward<=0:counts["bad_anchor_geometry"]+=1;continue
        risk_atr=risk/signal["signal_atr"]
        target_atr=reward/signal["signal_atr"]
        outcomes=[]
        for close,atr in options[:MAX_ATTEMPTS]:
            if len(outcomes)>=CONTROLS_PER_ANCHOR:break
            quote,err=first_quote(mt5,SYMBOL,close+.250,30.)
            if err:
                counts["control_entry_"+err]+=1;continue
            spread_ratio=(quote["ask"]-quote["bid"])/atr
            if spread_ratio>SPREAD_CAP or abs(spread_ratio-signal["entry_spread_div_atr"])>COST_RATIO_TOLERANCE:
                counts["unmatched_control_spread_ratio"]+=1;continue
            side=signal["side"]
            base=quote["ask"] if side=="BUY" else quote["bid"]
            risk_dist=risk_atr*atr
            target_dist=target_atr*atr
            if risk_dist<=info.trade_stops_level*info.point+info.trade_tick_size*4:
                counts["control_stop_too_close"]+=1;continue
            stop=base-risk_dist if side=="BUY" else base+risk_dist
            target=base+target_dist if side=="BUY" else base-target_dist
            ticks,error=tick_series(mt5,SYMBOL,quote,signal["max_hold_seconds"])
            if error:
                counts["control_path_"+error]+=1;continue
            control=simulate_structure(ticks,side,stop,target,
                    signal["max_hold_seconds"],info.trade_tick_size,STRESS_TICKS)
            if control["status"]!="CLOSED":
                counts["control_exit_"+control["status"]]+=1;continue
            outcomes.append(dict(
                control_signal_utc=datetime.fromtimestamp(close,UTC).isoformat(),
                control_atr=atr,control_spread_ratio=spread_ratio,
                control_R=control["R"],control_exit=control["exit_reason"],
                quote_sha256=sha256(json.dumps(
                    ticks,separators=(",",":"),allow_nan=False).encode()).hexdigest(),
                slippage_ticks_each_side=STRESS_TICKS))
        if not outcomes:
            counts["anchor_without_any_controls"]+=1;continue
        original=signal["R"]
        if original is None or signal["status"]!="CLOSED":
            counts["anchor_unpriced"]+=1;continue
        paired.append(dict(signal_utc=signal["entry_signal_close_utc"],
           phase=signal["research_window"],side=signal["side"],
           original_R=original,
           controls_succeeded=len(outcomes),
           average_control_R=mean(v["control_R"] for v in outcomes),
           lift_R=original-mean(v["control_R"] for v in outcomes),
           controls=outcomes,unvalidated=True))
        counts["matched_anchors"]+=1
        counts["completed_matched_control_positions"]+=len(outcomes)
    rmean=lambda rows,key:(mean(x[key] for x in rows) if rows else None)
    answer=dict(kind="NAS100_matched_timestamp_random_control_v1",
       registered_symbol=SYMBOL,fixed_seed=SEED,
       matching_contract=dict(target_controls_per_signal=CONTROLS_PER_ANCHOR,
           maximum_attempts=MAX_ATTEMPTS,nearest_time_window_minutes=120,
           minimum_time_separation_minutes=45,within_same_UTC_day=True,
           same_local_ny_session=True,relative_ATR_tolerance=ATR_TOLERANCE,
           absolute_spread_to_ATR_tolerance=COST_RATIO_TOLERANCE,
           identical_original_side=True,
           geometric_stop_and_target_scaled_to_control_ATR=True,
           slippage_adverse_ticks_each_side=STRESS_TICKS),
       matching_failures=dict(counts),
       matched_entries=len(paired),
       matched_control_positions=sum(x["controls_succeeded"] for x in paired),
       average_original_R=rmean(paired,"original_R"),
       average_control_R=rmean(paired,"average_control_R"),
       matched_average_R_lift=rmean(paired,"lift_R"),
       day_block_bootstrap_95pct_lift=bootstrap_pair(paired),
       methodological_limits=["Matched time and ATR are observable but not perfectly equal",
             "Control overlap and date-dependence; not a real portfolio",
             "Reused historical price periods; not untouched prospective OOS",
             "Real broker commission, queue fills and slippage unknown",
             "Bootstrap does not correct prior model search or multiple comparisons"],
       trade_decision="NO_TRADE",live_execution_enabled=False,
       model_promotion_allowed=False,matched_pairs=paired)
    return answer

def main():
    import MetaTrader5 as mt5
    p=argparse.ArgumentParser()
    p.add_argument("--report",nargs="+",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--terminal",default=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe")
    a=p.parse_args()
    output=Path(a.output)
    if output.exists():raise FileExistsError("immutable_control_output")
    anchors=[];manifest=[];seen=set()
    for f in a.report:
        raw=Path(f).read_bytes()
        data=json.loads(raw)
        if data.get("kind")!="distinct_per_symbol_research_playbooks_v1" or (
              data.get("live_execution_enabled") is not False):raise ValueError("invalid_shadow_input")
        manifest.append(dict(path=str(f),sha256=sha256(raw).hexdigest()))
        for trial in data["trials"]:
            if trial["symbol"]!=SYMBOL or trial["slippage_each_side_ticks"]!=1:
                continue
            key=(trial["research_window"],trial["quote_entry_utc"])
            if key in seen:raise ValueError("overlapping_input_archives")
            seen.add(key);anchors.append(trial)
    if not mt5.initialize(a.terminal,timeout=20000):
        raise RuntimeError("terminal_unavailable")
    try:
        result=run(mt5,anchors)
    finally:
        mt5.shutdown()
    result["evidence_sources"]=manifest
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("COUNTS",json.dumps(result["matching_failures"]))
    print("RESULT",json.dumps({k:result[k] for k in (
        "matched_entries","matched_control_positions","average_original_R",
        "average_control_R","matched_average_R_lift",
        "day_block_bootstrap_95pct_lift")}))
    print("REPORT",str(output))
if __name__=="__main__":
    main()
