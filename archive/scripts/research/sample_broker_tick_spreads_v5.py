"""Historical broker bid/ask tick spread spot-check; NOT full tick replay.

Query 1000 quote-change ticks at four pre-selected sessions for selected
instruments. A returned tick must be within 1 hour of target date to count.
Historical commission still must be verified separately.
"""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5
OUT=Path(r"C:\KatarinaDev\decision-backtest-20261012\intraday_scalp_full_m5_v5")
DATES=((2025,9,15),(2026,1,15),(2026,6,15),(2026,10,9))
SYMS=("EURUSD.vx","XAUUSD.vx","US30.vx","JPN225.vx")
def main():
    if not mt5.initialize():raise RuntimeError("MT5 missing")
    if mt5.terminal_info().trade_allowed:
        mt5.shutdown();raise RuntimeError("refuse running with live trading enabled")
    rows=[]
    for sym in SYMS:
        inf=mt5.symbol_info(sym)
        mt5.symbol_select(sym,True)
        point=float(inf.point)
        for y,m,d in DATES:
            dt=datetime(y,m,d,12,0,tzinfo=timezone.utc)
            a=mt5.copy_ticks_from(sym,dt,1000,mt5.COPY_TICKS_INFO)
            if a is None or len(a)<50:
                rows.append(dict(symbol=sym,requested=dt.isoformat(),
                    valid=False,count=0,reason="insufficient_tick_data"));continue
            diff=int(a["time"][0])-int(dt.timestamp())
            valid=0<=diff<=3600
            spreads=a["ask"]-a["bid"]
            spreads=spreads[np.isfinite(spreads)&(spreads>0)]
            rows.append(dict(symbol=sym,requested=dt.isoformat(),
                valid=valid,first_tick_dt_s=diff,
                count=len(a),positive_spread_ticks=len(spreads),
                spread_median_price=round(float(np.median(spreads)),9) if len(spreads) else None,
                spread_p90_price=round(float(np.quantile(spreads,.9)),9) if len(spreads) else None,
                spread_median_points=round(float(np.median(spreads))/point,2) if len(spreads) else None,
                spread_p90_points=round(float(np.quantile(spreads,.9))/point,2) if len(spreads) else None))
            print("TICK",sym,dt.date(),"valid",valid,
                "gap_sec",diff,"p50",rows[-1]["spread_median_points"],
                "p90",rows[-1]["spread_p90_points"],flush=True)
    mt5.shutdown()
    result=dict(kind="BROKER_HISTORIC_TICK_SPREAD_SPOT_CHECK",
        query_count=len(rows),usable_samples=sum(x["valid"] for x in rows),
        samples=rows,actual_execution_reconstruction=False,
        historical_commission_reconciled=False,
        historical_timezone_offset_verified=False,
        no_trades_executed=True)
    (OUT/"TICK_SPREAD_SAMPLES.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("TICK_AUDIT_FINAL",result["usable_samples"],"/",len(rows))
if __name__=="__main__":main()