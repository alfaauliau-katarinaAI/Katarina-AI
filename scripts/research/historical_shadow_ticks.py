"""Historical tick-quote diagnostic for KATARINA's frozen shadow hypothesis.

Read only. Never sends orders; evaluates historical signals causally.
Historical macro data are unavailable, so all observations are exploratory.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.intelligence.multi_market_brain import features
from katarina.intelligence.shadow_hypotheses import propose
from katarina.intelligence.technical_regime import classify_market_regime

UTC = timezone.utc
HORIZON = 900
WINDOW = 90
TARGETS = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "XAGUSD", "US30")


def bars(raw):
    return [{k: float(r[k]) for k in
             ("time", "open", "high", "low", "close", "tick_volume")}
            for r in raw]


def intact(rows, period):
    return (len(rows) == 120 and
            all(0 < rows[i]["time"] - rows[i-1]["time"] <= period*2
                for i in range(1, len(rows))))


def snapshot_hash(rows):
    return sha256(json.dumps(rows, sort_keys=True,
                             allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def first_quote(mt5, symbol, earliest, max_wait):
    start = datetime.fromtimestamp(earliest, UTC)
    stop = datetime.fromtimestamp(earliest + max_wait, UTC)
    arr = mt5.copy_ticks_range(symbol, start, stop, mt5.COPY_TICKS_ALL)
    if arr is None:
        return None, "tick_api_error"
    for tick in arr:
        stamp = float(tick["time_msc"])/1000
        bid, ask = float(tick["bid"]), float(tick["ask"])
        if earliest <= stamp <= earliest + max_wait and (
            all(isfinite(v) and v > 0 for v in (bid, ask)) and ask >= bid
        ):
            return dict(time=stamp, bid=bid, ask=ask), None
    return None, "quote_unavailable"


def scan_symbol(mt5, symbol, start, end, limit):
    info = mt5.symbol_info(symbol)
    if info is None:
        return {"symbol":symbol, "reason":"symbol_unknown"}
    if info.trade_mode not in (1, 2, 4):
        return {"symbol":symbol, "reason":"broker_trade_mode_denied"}
    if not mt5.symbol_select(symbol, True):
        return {"symbol":symbol, "reason":"symbol_subscription_failed"}
    # 16h warmup covers the 120 fully closed 5m candles, including quiet periods.
    warmup = start - timedelta(days=2)
    m1_raw = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, warmup, end)
    m5_raw = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, warmup, end)
    if m1_raw is None or m5_raw is None:
        return {"symbol":symbol,"reason":"bar_history_not_available",
                "last_error":mt5.last_error()}
    m1, m5 = bars(m1_raw), bars(m5_raw)
    m5_closes = [int(x["time"]+300) for x in m5]
    start_ts, end_ts = start.timestamp(), end.timestamp()
    allowed = {4:["BUY","SELL"],1:["BUY"],2:["SELL"]}[info.trade_mode]
    counters = Counter()
    signals = []
    last_chosen_until = float("-inf")
    for i in range(120, len(m1)):
        c = m1[i]
        stamp = c["time"] + 60
        if stamp < start_ts or stamp >= end_ts:
            continue
        counters["closed_m1_checked"] += 1
        if stamp < last_chosen_until:
            counters["overlap_skipped"] += 1
            continue
        lookback = m1[i-20:i]
        if len(lookback) != 20 or c["tick_volume"] < 1.25*mean(
                x["tick_volume"] for x in lookback):
            continue
        width = c["high"]-c["low"]
        if width <= 0 or abs(c["close"]-c["open"]) < 0.60*width:
            continue
        if not (c["close"] > max(b["high"] for b in m1[i-6:i]) or
                c["close"] < min(b["low"] for b in m1[i-6:i])):
            continue
        counters["quick_prefilter_pass"] += 1
        one_bars = m1[i-119:i+1]
        j = bisect_right(m5_closes, stamp)-1
        if j < 119:
            counters["missing_m5_warmup"] += 1
            continue
        five_bars = m5[j-119:j+1]
        if not intact(one_bars,60) or not intact(five_bars,300):
            counters["bar_gap"] += 1
            continue
        try:
            now = datetime.fromtimestamp(stamp,UTC)
            one = features(one_bars,60,now)
            five = features(five_bars,300,now)
        except ValueError:
            counters["features_invalid"] += 1
            continue
        if five["close_age_seconds"] > 600:
            counters["m5_stale"] += 1
            continue
        regime = classify_market_regime(five)
        row = {"m1":one, "m5":five, "m1_bars":one_bars,
               "regime_detail":regime, "allowed_sides":allowed}
        hypothesis = propose(row)
        if not hypothesis:
            counters["hypothesis_rejected"] += 1
            continue
        counters["hypothesis_pass"] += 1
        if len(signals) >= limit:
            counters["cap_reached"] += 1
            break
        entry, error = first_quote(mt5, symbol, stamp, WINDOW)
        if error:
            counters["entry_"+error] += 1
            continue
        spread_atr = (entry["ask"]-entry["bid"])/one["atr"]
        cost_gate_pass = spread_atr <= 0.15
        if not cost_gate_pass:
            counters["spread_above_0_15atr"] += 1
        else:
            counters["spread_gate_pass"] += 1
        # Even blocked proposals get a descriptive quote markout, but cannot
        # become tradable candidates or retrospectively override the gate.
        last_chosen_until = entry["time"]+HORIZON
        exit_quote, error = first_quote(mt5, symbol, entry["time"]+HORIZON, WINDOW)
        if error:
            counters["exit_"+error] += 1
            continue
        side = hypothesis[0]["side"]
        net_delta = (exit_quote["bid"]-entry["ask"]) if side == "BUY" else (
                     entry["bid"]-exit_quote["ask"])
        midpoint_entry = (entry["bid"]+entry["ask"])/2
        midpoint_exit = (exit_quote["bid"]+exit_quote["ask"])/2
        mid_delta = (midpoint_exit-midpoint_entry)*(1 if side=="BUY" else -1)
        signal = {
            "symbol":symbol, "side":side,
            "family":hypothesis[0]["family"],"regime":regime,
            "signal_bar_close_utc":datetime.fromtimestamp(stamp,UTC).isoformat(),
            "entry_tick_utc":datetime.fromtimestamp(entry["time"],UTC).isoformat(),
            "exit_tick_utc":datetime.fromtimestamp(exit_quote["time"],UTC).isoformat(),
            "entry_bid":entry["bid"],"entry_ask":entry["ask"],
            "exit_bid":exit_quote["bid"],"exit_ask":exit_quote["ask"],
            "entry_spread_atr":spread_atr,
            "spread_atr_gate_max":0.15,
            "cost_screen_pass":cost_gate_pass,
            "quoted_markout_bps":net_delta/midpoint_entry*10000,
            "midpoint_markout_bps":mid_delta/midpoint_entry*10000,
            "m1_evidence_sha256":snapshot_hash(one_bars),
            "m5_evidence_sha256":snapshot_hash(five_bars),
            "historical_macro_context":"UNAVAILABLE_POINT_IN_TIME",
            "is_realized_pnl":False,
            "live_risk_authorized":False
        }
        signals.append(signal)
        counters["quotes_measured"] += 1
    return {
        "symbol":symbol,"asset_class":"broker_metadata_not_historically_verified",
        "current_trade_mode":int(info.trade_mode),
        "m1_bars_available":len(m1),"m5_bars_available":len(m5),
        "first_m1_utc":datetime.fromtimestamp(m1[0]["time"],UTC).isoformat() if m1 else None,
        "last_m1_utc":datetime.fromtimestamp(m1[-1]["time"],UTC).isoformat() if m1 else None,
        "counts":dict(counters),"signals":signals,
    }


def execute(args):
    import MetaTrader5 as mt5
    start = datetime.strptime(args.start,"%Y-%m-%d").replace(tzinfo=UTC)
    end = datetime.strptime(args.end,"%Y-%m-%d").replace(tzinfo=UTC)
    if end <= start:
        raise ValueError("invalid date range")
    if end > datetime.now(UTC):
        raise ValueError("cannot evaluate future history")
    if not mt5.initialize(args.terminal, timeout=20000):
        raise RuntimeError("research_terminal_unavailable: "+str(mt5.last_error()))
    try:
        catalog = [s.name for s in (mt5.symbols_get() or ())]
        if args.symbols == "all":
            names = sorted(catalog)
        else:
            names = []
            for requested in args.symbols.split(","):
                requested = requested.strip().upper()
                match = next((name for name in catalog if name.upper().startswith(requested)),None)
                if match:
                    names.append(match)
        items = []
        for name in names:
            try:
                record = scan_symbol(mt5,name,start,end,args.max_signals_per_symbol)
                items.append(record)
                print(json.dumps({"symbol":name,
                     "m1":record.get("m1_bars_available",0),
                     "signals":len(record.get("signals",[])),
                     "counts":record.get("counts",{}),
                     "reason":record.get("reason")}),flush=True)
            except Exception as ex:
                items.append(dict(symbol=name,error=type(ex).__name__,
                                  detail=str(ex)[:160]))
                print(json.dumps(items[-1]),flush=True)
    finally:
        mt5.shutdown()
    all_signals = [s for r in items for s in r.get("signals",[])]
    metrics = {}
    for side in ("BUY","SELL"):
        metrics[side]={}
        for gate in (True,False):
            subgroup = [s["quoted_markout_bps"] for s in all_signals
                        if s["side"]==side and s["cost_screen_pass"]==gate]
            metrics[side]["spread_pass" if gate else "spread_reject"] = {
                "n":len(subgroup),
                "mean_quoted_markout_bps":mean(subgroup) if subgroup else None,
                "positive_fraction":sum(x>0 for x in subgroup)/len(subgroup)
                if subgroup else None}
    result = {
        "report_version":"historical_tick_shadow_v1",
        "period":{"start":args.start,"end_exclusive":args.end},
        "research_scope":"EXPLORATORY_REUSED_HISTORY_NOT_PROSPECTIVE",
        "terminal":args.terminal,"family":"trend_impulse_break_v1",
        "timeframes":["M1","M5"],"horizon_seconds":HORIZON,
        "entry_exit_quotes":"first_MT5_bid_ask_tick_within_90s",
        "tick_quote_source":"broker_historical_copy_ticks_range",
        "broker_side_permission":"current_snapshot_only",
        "historical_macro_context":"NOT_AVAILABLE_DO_NOT_BACKFILL_CURRENT_NEWS",
        "commission_included":False,"slippage_included":False,
        "stop_loss_take_profit_paths_tested":False,
        "live_execution_enabled":False,"model_promotion_allowed":False,
        "cost_rejected_observations_are_descriptive_only":True,
        "symbols_scanned":len(items),"signals_observed":len(all_signals),
        "summary_by_side":metrics,"symbols":items,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():
        raise FileExistsError("immutable historical run exists: "+str(out))
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("REPORT "+str(out),flush=True)
    print("RESULT "+json.dumps({"symbols":len(items),"signals":len(all_signals),
                                "sides":metrics}),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--terminal",default=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe")
    parser.add_argument("--start",required=True)
    parser.add_argument("--end",required=True)
    parser.add_argument("--symbols",default=",".join(TARGETS))
    parser.add_argument("--max-signals-per-symbol",type=int,default=200)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    if not 1<=args.max_signals_per_symbol<=500:
        parser.error("invalid cap")
    execute(args)


if __name__=="__main__":
    main()
