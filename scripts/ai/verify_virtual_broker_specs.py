"""One-shot broker-native risk-geometry diagnostics WITHOUT ORDER SUBMISSION.

Reads MT5 contract, tick, lot min/step, and native profit/margin calculators
for at most 17 broker-advertised symbols. No account records or trade writes.
Private local output only. Calculator output is not verified commission,
slippage, cent-account denomination, or a guarantee of executability.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from katarina.intelligence.broker.broker_scan_universe import resolve_broker_symbols
from katarina.intelligence.broker.broker_clock_alignment import infer_clock_shift


def run():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("MT5_NOT_CONNECTED")
    try:
        term=mt5.terminal_info()
        if term is None or term.trade_allowed:
            raise RuntimeError("FAIL_CLOSED_TRADE_PERMISSION_MUST_BE_DISABLED")
        now=datetime.now(timezone.utc)
        universe=resolve_broker_symbols(mt5.symbols_get())
        symbols=list(universe.symbols)
        tickmap={s:mt5.symbol_info_tick(s) for s in symbols}
        shift=infer_clock_shift(
            {sym:int(t.time) for sym,t in tickmap.items()
             if t is not None and t.bid>0 and t.ask>=t.bid},
            now.timestamp(),
        )
        if not shift.suitable_for_readonly_snapshot:
            raise RuntimeError("UNTRUSTED_BROKER_CLOCK")
        rows=[]
        for s in symbols:
            q=tickmap.get(s)
            info=mt5.symbol_info(s)
            if not q or not info:
                rows.append({"symbol":s,"status":"QUOTE_OR_CONTRACT_MISSING"})
                continue
            try:
                size=float(info.trade_tick_size or info.point)
                minimum=float(info.volume_min)
                step=float(info.volume_step)
                contract=float(info.trade_contract_size)
                tickval=float(info.trade_tick_value)
                volume=minimum
                price=float(q.ask)
                direction=mt5.ORDER_TYPE_BUY
                favorable=price+max(10*size,info.point)
                loss=price-max(10*size,info.point)
                # These APIs CALCULATE; they do not place orders or
                # authorize risk allocation.
                profit=mt5.order_calc_profit(direction,s,volume,price,favorable)
                risk=mt5.order_calc_profit(direction,s,volume,price,loss)
                margin=mt5.order_calc_margin(direction,s,volume,price)
                rows.append({
                    "symbol":s,"status":"BROKER_NATIVE_CALCULATOR_AVAILABLE" if
                        profit is not None and risk is not None and margin is not None
                        else "BROKER_NATIVE_CALCULATOR_UNAVAILABLE",
                    "volume_min":minimum,"volume_step":step,
                    "tick_size":size,"tick_value_reported":tickval,
                    "contract_size":contract,
                    "trade_mode":int(info.trade_mode),
                    "min_volume_10tick_profit_account_currency":round(profit,6) if profit is not None else None,
                    "min_volume_10tick_loss_account_currency":round(risk,6) if risk is not None else None,
                    "min_volume_estimated_margin_account_currency":round(margin,6) if margin is not None else None,
                    "quote_staleness_s":round(now.timestamp()-(int(q.time)-shift.observed_hours_shift*3600),2),
                })
            except (ValueError,TypeError,OverflowError) as e:
                rows.append({"symbol":s,"status":"CALCULATOR_EXCEPTION_"+type(e).__name__})
        return {
            "as_of_utc":now.isoformat(),
            "purpose":"READ_ONLY_PRIVATE_BROKER_EXECUTION_GEOMETRY_PREFLIGHT",
            "symbols_examined":len(rows),
            "broker_clock_offset_now_hours":shift.observed_hours_shift,
            "rows":rows,
            "terminal_trade_permission":False,
            "orders_sent":0,
            "real_commission_verified":False,
            "swap_verified":False,
            "actual_slippage_verified":False,
            "deposit_currency_and_cent_classification_verified":False,
            "historical_dst_alignment_verified":False,
            "live_execution_authorized":False,
        }
    finally:
        mt5.shutdown()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--private-output",required=True)
    a=p.parse_args()
    target=Path(a.private_output)
    if target.suffix!=".json":
        p.error("private JSON file required")
    result=run()
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    tmp.replace(target)
    print("READ_ONLY_NATIVE_MT5_PREFLIGHT",json.dumps({
        "symbols":result["symbols_examined"],
        "calculator_available":sum(x["status"]=="BROKER_NATIVE_CALCULATOR_AVAILABLE"
                                   for x in result["rows"]),
        "calculator_unavailable":[x["symbol"] for x in result["rows"]
                                  if x["status"]!="BROKER_NATIVE_CALCULATOR_AVAILABLE"],
        "live_authorized":False,"orders_sent":0}))


if __name__=="__main__":
    main()
