"""Audit historical KATARINA tick-quote evidence across immutable windows."""
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from statistics import mean,median
import argparse,json,math

def iso_time(s):
    t=datetime.fromisoformat(s)
    if t.tzinfo is None: raise ValueError("naive clock")
    return t.timestamp()

def audit(paths):
    all_signals=[]
    windows=[]
    for path in paths:
        blob=path.read_bytes()
        obj=json.loads(blob)
        if obj.get("report_version")!="historical_tick_shadow_v1":
            raise ValueError("invalid report")
        if obj.get("live_execution_enabled") is not False or obj.get("model_promotion_allowed") is not False:
            raise ValueError("unexpected live authorization")
        signals=[s for row in obj["symbols"] for s in row.get("signals",[])]
        if len(signals)!=obj["signals_observed"]:
            raise ValueError("inconsistent signal count")
        for s in signals:
            entry=iso_time(s["entry_tick_utc"])
            close=iso_time(s["signal_bar_close_utc"])
            finish=iso_time(s["exit_tick_utc"])
            if not 0<=entry-close<=90 or not 900<=finish-entry<=990:
                raise ValueError("lookahead, early tick or late quote")
            bid,ask,xbid,xask=(s[k] for k in
                ("entry_bid","entry_ask","exit_bid","exit_ask"))
            if not all(math.isfinite(x) and x>0 for x in (bid,ask,xbid,xask)):
                raise ValueError("invalid tick")
            if bid>ask or xbid>xask:
                raise ValueError("crossed quote")
            expected=(xbid-ask if s["side"]=="BUY" else bid-xask)/((bid+ask)/2)*10000
            if abs(s["quoted_markout_bps"]-expected)>1e-7:
                raise ValueError("incorrect spread charge")
            if s.get("is_realized_pnl") is not False or s.get("live_risk_authorized") is not False:
                raise ValueError("wrong evidence type")
        windows.append(dict(source=str(path),sha256=sha256(blob).hexdigest(),
            period=obj["period"],symbols=len(obj["symbols"]),
            with_m1_history=sum(bool(row.get("m1_bars_available")) for row in obj["symbols"]),
            measured=len(signals),cost_pass=sum(s["cost_screen_pass"] for s in signals)))
        all_signals.extend(signals)
    groups=defaultdict(list)
    for s in all_signals:
        groups[(s["symbol"],s["side"],s["cost_screen_pass"])].append(s)
    by_symbol=[]
    for (symbol,side,cost),arr in sorted(groups.items()):
        values=[s["quoted_markout_bps"] for s in arr]
        dates={s["signal_bar_close_utc"][:10] for s in arr}
        by_symbol.append(dict(symbol=symbol,side=side,cost_screen_pass=cost,
            observations=len(arr),dates=len(dates),
            mean_quoted_markout_bps=mean(values),
            median_quoted_markout_bps=median(values),
            positive_fraction=sum(x>0 for x in values)/len(values),
            descriptive_sample_ok=len(arr)>=30 and len(dates)>=10,
            model_promotion_allowed=False))
    by_group=[]
    for side in ("BUY","SELL"):
        for pass_gate in (True,False):
            arr=[s for s in all_signals if s["side"]==side and
                 s["cost_screen_pass"]==pass_gate]
            values=[s["quoted_markout_bps"] for s in arr]
            by_group.append(dict(side=side,cost_screen_pass=pass_gate,
                observations=len(arr),
                avg_quoted_markout_bps=mean(values) if values else None,
                positive_fraction=sum(x>0 for x in values)/len(values) if values else None))
    return dict(kind="historical_tick_quote_replay_not_strategy_pnl",
        input_windows=windows,signals=len(all_signals),group_summary=by_group,
        per_symbol_side=by_symbol,model_promotion_allowed=False,
        commission_slippage_included=False,macro_point_in_time_unavailable=True,
        windows_not_prospectively_untouched=True,
        warning="Signals are closed-candle shadow proposals, not executable historical portfolio fills.")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True,nargs="+")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    paths=[Path(x) for x in args.report]
    result=audit(paths)
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise FileExistsError("audit file already exists")
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("signals","input_windows","group_summary")},indent=2))
    print("AUDIT "+str(target))

if __name__=="__main__":
    main()
