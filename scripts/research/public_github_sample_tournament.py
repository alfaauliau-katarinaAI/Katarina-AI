"""Research tournament using independent public GitHub 5m OHLCV samples.

This path deliberately labels spread/ASK as *MODELED*, unlike the
BID/ASK-validated Dukascopy path (which may be unavailable to GitHub runners).
Public vendor samples are exploratory and not broker-verified.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
from io import StringIO
import json
from pathlib import Path
import sys
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from katarina.intelligence.lab.adaptive_strategy_library import (
    propose_closed_candle_strategies)
from public_market_tournament import (
    QuoteCandle, calculate_fill, metrics, SCALE)

# Verified public sample repositories: 5m reference OHLC, NOT paired bid/ask.
PUBLIC_SAMPLES={
    "EURUSD": ("getdata-finance/eurusd-5m-ohlcv-forex-historical-data","EURUSD_5m.csv",.00020),
    "GBPUSD": ("getdata-finance/gbpusd-5m-ohlcv-forex-historical-data","GBPUSD_5m.csv",.00025),
    "USDJPY": ("getdata-finance/usdjpy-5m-ohlcv-forex-historical-data","USDJPY_5m.csv",.025),
    "AUDUSD": ("getdata-finance/audusd-5m-ohlcv-forex-historical-data","AUDUSD_5m.csv",.00020),
    "USDCAD": ("getdata-finance/usdcad-5m-ohlcv-forex-historical-data","USDCAD_5m.csv",.00022),
    "EURGBP": ("getdata-finance/eurgbp-5m-ohlcv-forex-historical-data","EURGBP_5m.csv",.00016),
    "EURJPY": ("getdata-finance/eurjpy-5m-ohlcv-forex-historical-data","EURJPY_5m.csv",.030),
    "XAUUSD": ("getdata-finance/xauusd-5m-ohlcv-metals-historical-data","XAUUSD_5m.csv",.40),
    "USOIL": ("getdata-finance/usoil-5m-ohlcv-commodities-historical-data","USOIL_5m.csv",.05),
    "US30": ("getdata-finance/us30-5m-ohlcv-index-historical-data","US30_5m.csv",4.0),
    "NAS100": ("getdata-finance/nas100-5m-ohlcv-index-historical-data","NAS100_5m.csv",3.0),
}
POINT_SCALE=dict(SCALE, USOIL=100, US30=1, NAS100=1)
UNVERIFIED_SCOPE=("USDCHF","NZDUSD","GBPJPY","AUDJPY","EURAUD","BTCUSD")
MAX_CSV_BYTES=7_500_000


def load_public_sample(symbol: str, begin: date, end: date, *, opener=urlopen):
    if symbol not in PUBLIC_SAMPLES or not begin<end:
        raise ValueError("unverified_public_github_sample")
    repo,name,assumed_spread=PUBLIC_SAMPLES[symbol]
    url=f"https://raw.githubusercontent.com/{repo}/main/{name}"
    try:
        with opener(Request(url,headers={"User-Agent":"Katarina-Public-Research/1.0"}),
                    timeout=45) as response:
            content=response.read(MAX_CSV_BYTES+1)
    except (HTTPError,URLError,TimeoutError) as e:
        raise RuntimeError("public_github_sample_unavailable") from e
    if len(content)>MAX_CSV_BYTES or not content:
        raise ValueError("empty_or_oversized_public_sample")
    reader=csv.DictReader(StringIO(content.decode("utf-8-sig")))
    if not {"datetime","open","high","low","close"}.issubset(reader.fieldnames or []):
        raise ValueError("unexpected_public_sample_schema")
    rows=[]
    counts=Counter()
    start=datetime(begin.year,begin.month,begin.day,tzinfo=timezone.utc)
    finish=datetime(end.year,end.month,end.day,tzinfo=timezone.utc)
    previous=None
    for data in reader:
        dt=datetime.fromisoformat(data["datetime"].replace("Z","+00:00"))
        if dt.tzinfo is None:
            raise ValueError("unknown_market_timezone")
        instant=dt.astimezone(timezone.utc)
        if instant<start or instant>=finish:
            continue
        if dt.minute%5 or dt.second or dt.microsecond:
            raise ValueError("not_M5_chart_data")
        op,hi,lo,cl=(float(data[k]) for k in
                     ("open","high","low","close"))
        if not (0<lo<=min(op,cl)<=max(op,cl)<=hi):
            raise ValueError("invalid_public_sample_ohlc")
        stamp=int(instant.timestamp())+300
        if previous is not None and stamp<=previous:
            raise ValueError("unsorted_or_duplicate_public_sample")
        previous=stamp
        # Public OHLC is a reference price; the bid/ask sides here are
        # scenario assumptions and NOT source-provided BID/ASK evidence.
        rows.append(QuoteCandle(
            stamp,op,hi,lo,cl,
            op+assumed_spread,hi+assumed_spread,
            lo+assumed_spread,cl+assumed_spread))
        counts["m5"]+=1
    return rows,{
        "source":url,"m5_reference_bars":len(rows),
        "actual_historical_bid_ask_available":False,
        "model_spread_price":assumed_spread,
        "modeled_bid_equals_public_reference_ohlc":True,
        "not_independent_holdout":True,
    }


def h1_from_m5(m5: list[QuoteCandle]):
    groups=defaultdict(list)
    for b in m5:
        bucket=((b.time-1)//3600+1)*3600
        groups[bucket].append(b)
    out=[]
    for at,rows in sorted(groups.items()):
        if len(rows)!=12 or rows[0].time!=at-3300 or rows[-1].time!=at:
            continue
        if any(y.time-x.time!=300 for x,y in zip(rows,rows[1:])):
            continue
        out.append(QuoteCandle(
            at,rows[0].bid_open,max(v.bid_high for v in rows),
            min(v.bid_low for v in rows),rows[-1].bid_close,
            rows[0].ask_open,max(v.ask_high for v in rows),
            min(v.ask_low for v in rows),rows[-1].ask_close))
    return out


def tournament(symbol: str,m5: list[QuoteCandle],*,fee=.03,slip_points=1):
    if symbol not in PUBLIC_SAMPLES:
        raise ValueError("symbol_not_research_approved")
    h1=h1_from_m5(m5)
    if len(m5)<80 or len(h1)<16:
        return [],{"status":"INSUFFICIENT_HISTORY","m5":len(m5),"h1":len(h1)}
    hclock=[x.time for x in h1]
    trades=[]
    stats=Counter()
    open_until={}
    for idx in range(29,len(m5)-25):
        now=m5[idx].time
        prior=m5[idx-29:idx+1]
        if any(y.time-x.time!=300 for x,y in zip(prior,prior[1:])):
            stats["m5_gap"]+=1
            continue
        hcount=bisect_right(hclock,now)
        if hcount<16 or m5[idx+1].time!=now+300:
            stats["h1_warmup_or_gap"]+=1
            continue
        hwindow=h1[hcount-16:hcount]
        signals=propose_closed_candle_strategies(
            symbol,tuple(x.bid() for x in prior),
            tuple(x.bid() for x in hwindow),now=now,
            point=1/POINT_SCALE[symbol],
            spread=m5[idx].spread_close())
        stats["signals"]+=len(signals)
        for s in signals:
            key=(s.strategy_id,s.side)
            if open_until.get(key,0)>now:
                stats["overlap_wait"]+=1
                continue
            future=m5[idx+1:idx+25]
            if any(y.time-x.time!=300 for x,y in zip(future,future[1:])):
                stats["exit_window_gap"]+=1
                continue
            t=calculate_fill(
                s,m5[idx+1],future,
                assumed_fee_r=fee,slippage_point=slip_points/POINT_SCALE[symbol])
            if t is not None:
                open_until[key]=t["exit_at"]
                trades.append(t)
    return trades,{"status":"OK","m5":len(m5),"h1":len(h1),
                   **dict(stats)}


def run(symbols,begin,end,destination: Path,*,opener=urlopen):
    if len(symbols)<1 or len(symbols)>4 or len(set(symbols))!=len(symbols):
        raise ValueError("pilot_max_4_symbols")
    destination.mkdir(parents=True,exist_ok=True)
    summary={
        "scope":"EXPLORATORY_4_STRATEGY_FAMILY_PILOT",
        "period":[begin.isoformat(),end.isoformat()],
        "source_kind":"PUBLIC_REFERENCE_M5_MODELED_BID_ASK",
        "actual_bid_ask_verified":False,"broker_costs_verified":False,
        "independent_holdout":False,"production":"WAIT",
        "risk_governor_changed":False,"orders_sent":0,
        "symbols":{},
        "scientific_limitations":[
            "Public reference M5 OHLC is not the broker VPS feed",
            "ASK/bid and spread are modeled, not genuine historical quotes",
            "Stop/target path within M5 is unresolved and pessimistically stop-first",
            "Risk scaling, broker commissions/swap and margin are unvalidated",
            "These 2026 periods overlap with previously researched history",
            "Pilot length is far below what is needed for robust strategy promotion",
        ],
    }
    trades_all=[]
    for symbol in symbols:
        candles,source=load_public_sample(symbol,begin,end,opener=opener)
        trades,scan=tournament(symbol,candles)
        outcomes={}
        buckets=defaultdict(list)
        for t in trades:
            buckets[(t["strategy"],t["side"],t["regime"])].append(t)
        for (method,side,regime),items in buckets.items():
            outcomes[f"{method}/{side}/{regime}"]={
                "base":metrics(items),"extra_0_1R":metrics(items,.1),
                "extra_0_2R":metrics(items,.2),
                "validated_edge":False}
        summary["symbols"][symbol]={
            "public_sample":source,"scanner":scan,
            "all_paper_trades":metrics(trades),"outcomes":outcomes,
            "method_counts":dict(Counter(x["strategy"] for x in trades))}
        trades_all.extend(trades)
        print("RESEARCH_SAMPLE",symbol,scan,metrics(trades),flush=True)
    # Compare fixed candidate families independently; these experiments can
    # overlap in time, so a cross-method compounded equity is NOT investable.
    method_buckets=defaultdict(list)
    for row in trades_all:
        method_buckets[(row["strategy"],row["side"])].append(row)
    split_time=int(datetime(
        begin.year,begin.month,begin.day,tzinfo=timezone.utc).timestamp()) + (
        (end-begin).days//2)*86400
    summary["method_groups"]={}
    for (method,side),rows in sorted(method_buckets.items()):
        first=[r for r in rows if r["signal_at"]<split_time]
        last=[r for r in rows if r["signal_at"]>=split_time]
        key=f"{method}/{side}"
        summary["method_groups"][key]={
            "base":metrics(rows),"extra_0_10R":metrics(rows,.1),
            "extra_0_20R":metrics(rows,.2),
            "early_window":metrics(first),"late_window":metrics(last),
            "confidence":"EXPLORATORY_ONLY",
            "broker_validated":False,"live_promotion_approved":False}
        print("METHOD_GROUP",key,summary["method_groups"][key],flush=True)
    # Pre-declared calendar-month screen. Research priority only;
    # no tuning or live promotion based on the same inspected data.
    summary["missing_6_priority_symbols"]=list(UNVERIFIED_SCOPE)
    summary["monthly_strategy_screen"]={}
    months=("2026-06","2026-07","2026-08")
    for symbol in symbols:
        for strategy in (
            "TREND_PULLBACK","BREAKOUT_RETEST",
            "LIQUIDITY_SWEEP_RECLAIM","RANGE_MEAN_REVERSION"):
            for side in ("BUY","SELL"):
                subset=[t for t in trades_all if (
                    t["symbol"]==symbol and t["strategy"]==strategy
                    and t["side"]==side)]
                monthly={}
                for month in months:
                    selected=[t for t in subset if datetime.fromtimestamp(
                        t["signal_at"],timezone.utc).strftime("%Y-%m")==month]
                    monthly[month]={
                        "base":metrics(selected),
                        "extra_0_10R":metrics(selected,.1),
                        "extra_0_20R":metrics(selected,.2)}
                # The pass flag is a RESEARCH triage indicator, not an edge
                # validation; exploratory data were previously exposed.
                pass_screen=all(
                    monthly[m]["extra_0_10R"]["n"]>=20 and
                    (monthly[m]["extra_0_10R"]["profit_factor"] or 0)>=1.2 and
                    (monthly[m]["extra_0_10R"]["avg_r"] or -99)>=.1
                    for m in months)
                summary["monthly_strategy_screen"][
                    "|".join((symbol,strategy,side))]={
                    "all_3_months":metrics(subset,.1),
                    "months":monthly,
                    "passed_exploratory_screen":pass_screen,
                    "evidence":"PREVIOUSLY_INSPECTED_EXPLORATORY",
                    "live_promotion_authorized":False}
    summary["screen_contract"]={
        "months":list(months),"min_trades_each_month":20,
        "min_after_stress_pf_each_month":1.2,
        "min_after_stress_mean_r_each_month":0.1,
        "real_bid_ask_verified":False,
        "independent_out_of_sample":False,
        "production_action":"WAIT"}
    summary["all_symbols"]=metrics(trades_all)
    summary["pooled_overlap_not_an_executable_portfolio"]=True
    summary["all_symbols_is_investable_portfolio"]=False
    summary["scientific_limitations"].append(
        "Hypothetical methods overlap and pooled compounding is NOT a feasible portfolio return")
    (destination/"summary.json").write_text(
        json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8")
    if trades_all:
        with (destination/"paper_trades.csv").open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=list(trades_all[0]))
            writer.writeheader();writer.writerows(trades_all)
    print("TOURNAMENT_PILOT",json.dumps({
        "symbols":list(summary["symbols"]),"trades":len(trades_all),
        "metrics":summary["all_symbols"],"orders_sent":0,
        "historical_bid_ask_verified":False},ensure_ascii=False),flush=True)
    return summary


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--symbols",default="EURUSD,XAUUSD")
    ap.add_argument("--start",default="2026-06-01")
    ap.add_argument("--end",default="2026-09-01")
    ap.add_argument("--output",type=Path,default=Path("artifacts/public_tournament"))
    a=ap.parse_args()
    run([s.strip().upper() for s in a.symbols.split(",")],
        date.fromisoformat(a.start),date.fromisoformat(a.end),a.output)


if __name__=="__main__":
    main()
