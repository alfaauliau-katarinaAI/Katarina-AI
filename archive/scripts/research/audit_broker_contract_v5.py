"""Read-only broker contract feasibility of paper V5 portfolio.

Risk model assumes fractional lot sizes. This audit checks minimum volume,
broker tick size/value and stops level at CURRENT symbol_info only. It cannot
replace historical conversion/margin, commissions or actual tick fills.
"""
from __future__ import annotations
import csv,json
from collections import defaultdict,Counter
from pathlib import Path
import MetaTrader5 as mt5
ROOT=Path(r"C:\KatarinaDev\decision-backtest-20261012\intraday_scalp_full_m5_v5")
CAPITAL_SCENARIOS=(1000.,5000.,10000.)
def main():
    events=list(csv.DictReader((ROOT/"COMBINED_POLICY_TRADES.csv").open(encoding="utf-8")))
    if not mt5.initialize():raise RuntimeError("MT5 unavailable")
    if mt5.terminal_info().trade_allowed:
        mt5.shutdown();raise RuntimeError("cannot audit with trading enabled")
    account=mt5.account_info()
    ccy=account.currency if account else "UNKNOWN"
    counts=Counter();by_asset=defaultdict(lambda:Counter())
    nonzero=[];details=[]
    for x in events:
        symbol=x["symbol"]
        s=mt5.symbol_info(symbol)
        if s is None:
            counts["missing_symbol_info"]+=1;continue
        step=float(s.volume_step)
        tick=float(s.trade_tick_size)
        tv=float(s.trade_tick_value_loss)
        minlot=float(s.volume_min)
        point=float(s.point)
        risk=float(x["risk_price"])
        if not all(y>0 for y in (step,tick,tv,minlot,point,risk)):
            counts["unknown_risk_conversion"]+=1;continue
        frac=.0025 if x["mode"]=="INTRADAY" else .001
        minimum_risk_ccy=(risk/tick)*tv*minlot
        stops_level=float(s.trade_stops_level)*point
        allowed_stop=risk>=stops_level
        if not allowed_stop:counts["below_broker_stops_level"]+=1
        required_capital=minimum_risk_ccy/frac
        nonzero.append(required_capital)
        for capital in CAPITAL_SCENARIOS:
            feasible=minimum_risk_ccy<=capital*frac and allowed_stop
            counts[f"feasible_{int(capital)}"]+=feasible
            by_asset[symbol][f"feasible_{int(capital)}"]+=feasible
        by_asset[symbol]["selected"]+=1
        details.append(dict(symbol=symbol,mode=x["mode"],
            hypothetical_min_equity_account_ccy=round(required_capital,2),
            minimum_lot=minlot,minimum_lot_risk_account_ccy=round(minimum_risk_ccy,3),
            stop_points=round(risk/point,2),
            current_broker_stops_level_points=s.trade_stops_level,
            stops_level_compatible=allowed_stop))
    mt5.shutdown()
    nonzero.sort()
    length=len(nonzero)
    q=lambda p:round(nonzero[int((length-1)*p)],2) if nonzero else None
    report=dict(kind="BROKER_SYMBOL_MIN_LOT_AND_STOP_COMPATIBILITY_V5",
        account_currency=ccy,reference_total_trade_entries=len(events),
        analyzed_trade_entries=length,current_only=True,
        current_tick_values_not_historical=True,
        commission_history_unavailable=True,
        spread_already_in_V5_next_open_fill=True,
        counts=dict(counts),
        minimum_equity_quantiles_account_ccy=dict(p10=q(.10),p50=q(.50),p90=q(.90)),
        hypothetical_capital=CAPITAL_SCENARIOS,
        instruments={k:dict(v) for k,v in sorted(by_asset.items())},
        notes=[
          "Numbers are scenario examples in the account deposit currency, not assumption about user's capital",
          "Current symbol tick values may differ historically due conversion and broker contract changes",
          "Requires full broker margin and free-equity checks, minimum lot step/risk alignment",
          "Commission roundtrip per lot not known from symbol_info. Cost shocks remain hypothetical",
          "This audit does not authorize live orders",
        ],orders_sent=0,live_execution_authorized=False)
    (ROOT/"BROKER_CONTRACT_AUDIT.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    with (ROOT/"contract_feasibility_selected.csv").open("w",newline="",encoding="utf-8") as f:
        if details:
            w=csv.DictWriter(f,fieldnames=list(details[0]));w.writeheader();w.writerows(details)
    print("BROKER_AUDIT",json.dumps({
      "account_currency":ccy,"entries":length,"summary":dict(counts),
      "min_capital_quantiles":report["minimum_equity_quantiles_account_ccy"]
    },ensure_ascii=False),flush=True)
if __name__=="__main__":main()