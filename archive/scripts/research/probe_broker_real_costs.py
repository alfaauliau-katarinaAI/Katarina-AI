"""Read-only broker symbol and executed-deal fee evidence; no identifiers/output credentials."""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime,timezone
from statistics import median
import MetaTrader5 as mt5

TERMINAL=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe"
PREFIXES=("XAUUSD","NAS100","US30","JPN225","EURUSD","GBPUSD","USDJPY",
          "XAGUSD","BTCUSD","AUDUSD")
def main():
    if not mt5.initialize(TERMINAL,timeout=20000):
        raise RuntimeError("broker_research_terminal_unavailable")
    result={"source":"current_MT5_broker_server_read_only","connected":False,
            "current_account_contracts_are_not_historical_fee_schedule":True,
            "symbols":[],"deal_history":{}}
    try:
        account=mt5.account_info()
        terminal=mt5.terminal_info()
        result["connected"]=bool(terminal and terminal.connected)
        result["account"]=dict(
            currency=getattr(account,"currency",None),
            trade_mode=getattr(account,"trade_mode",None),
            margin_mode=getattr(account,"margin_mode",None),
            leverage=getattr(account,"leverage",None),
            company=getattr(account,"company",None),
            trade_allowed=getattr(account,"trade_allowed",None))
        available=[x.name for x in (mt5.symbols_get() or ())]
        for prefix in PREFIXES:
            name=next((n for n in available if n.startswith(prefix+".vx")),None)
            if name is None:continue
            info=mt5.symbol_info(name)
            if not info:continue
            mt5.symbol_select(name,True)
            quote=mt5.symbol_info_tick(name)
            rec=dict(symbol=name, trade_mode=info.trade_mode,
                contract_size=info.trade_contract_size,
                digits=info.digits,point=info.point,tick_size=info.trade_tick_size,
                tick_value_profit=info.trade_tick_value_profit,
                tick_value_loss=info.trade_tick_value_loss,
                volume_min=info.volume_min,volume_step=info.volume_step,
                volume_max=info.volume_max,
                stops_level_points=info.trade_stops_level,
                freeze_level_points=info.trade_freeze_level,
                trade_calc_mode=info.trade_calc_mode,
                currency_base=info.currency_base,currency_profit=info.currency_profit,
                currency_margin=info.currency_margin,
                spread_points_snapshot=info.spread,
                swap_mode=info.swap_mode,swap_long=info.swap_long,
                swap_short=info.swap_short)
            if quote is not None and quote.bid>0 and quote.ask>=quote.bid:
                rec["quote_age_seconds"]=datetime.now(timezone.utc).timestamp()-quote.time_msc/1000
                rec["snapshot_spread_price"]=quote.ask-quote.bid
                # read-only order_calc_profit uses quote-based conversion at
                # current terminal quote; not guaranteed valid for historical FX.
                volume=info.volume_min
                delta=info.trade_tick_size*100
                for direction,tag in ((mt5.ORDER_TYPE_BUY,"buy"),(mt5.ORDER_TYPE_SELL,"sell")):
                    opening=quote.ask if tag=="buy" else quote.bid
                    closing=opening+(delta if tag=="buy" else -delta)
                    rec["calc_profit_"+tag+"_minlot_100ticks"]=mt5.order_calc_profit(
                        direction,name,volume,opening,closing)
            result["symbols"].append(rec)
        deals=mt5.history_deals_get(datetime(2026,1,1,tzinfo=timezone.utc),
                                    datetime.now(timezone.utc))
        if deals is None:
            result["deal_history"]={"source_available":False,
                "mt5_error_type":str(mt5.last_error()[0])}
        else:
            sums=defaultdict(lambda:dict(count=0,volume=0.,commission=0.,
                fee=0.,swap=0.,nonzero_commission_count=0))
            for deal in deals:
                symbol=str(getattr(deal,"symbol",""))
                if not symbol:continue
                slot=sums[symbol]
                slot["count"]+=1
                slot["volume"]+=float(getattr(deal,"volume",0.))
                slot["commission"]+=float(getattr(deal,"commission",0.))
                slot["fee"]+=float(getattr(deal,"fee",0.))
                slot["swap"]+=float(getattr(deal,"swap",0.))
                slot["nonzero_commission_count"]+=int(float(getattr(deal,"commission",0.))!=0)
            result["deal_history"]={"source_available":True,
                "total_deals":len(deals),
                "with_symbol":sum(x["count"] for x in sums.values()),
                "aggregated_by_symbol":dict(sums),
                "warning":"Commission zero in deals cannot certify zero future fees; only realized history."}
    finally:
        mt5.shutdown()
    print(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__":
    main()
