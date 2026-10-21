"""Read-only broker commission rate coverage summary, no account identifiers."""
from datetime import datetime,timezone,timedelta
from collections import defaultdict
import json
import MetaTrader5 as mt5
from pathlib import Path
out=Path(r"C:\KatarinaDev\decision-backtest-20261012\intraday_brain_integrated_v6")
out.mkdir(exist_ok=True,parents=True)
if not mt5.initialize():raise RuntimeError("mt5_no_connection")
if mt5.terminal_info().trade_allowed:
    mt5.shutdown();raise RuntimeError("refuse_trade_enabled")
now=datetime.now(timezone.utc)
deals=mt5.history_deals_get(now-timedelta(days=120),now)
account=mt5.account_info()
currency=(account.currency if account is not None else None)
summary={}
if deals is None:
    note="broker_deal_history_unavailable"
else:
    stats=defaultdict(lambda:dict(deals=0,commission_deals=0,volume=0.,abs_commission=0.))
    for x in deals:
        sym=str(x.symbol)
        if not sym:continue
        s=stats[sym]
        s["deals"]+=1
        if x.volume>0:s["volume"]+=float(x.volume)
        if abs(x.commission)>1e-12:
            s["commission_deals"]+=1;s["abs_commission"]+=abs(float(x.commission))
    summary={k:{
        "deals":v["deals"],"commission_deals":v["commission_deals"],
        "abs_commission_per_volume_across_deals":(
           round(v["abs_commission"]/v["volume"],5) if v["volume"] else None)}
        for k,v in stats.items()}
    note="commission_per_volume_is_one_deal_not_roundtrip; only if deal history and current symbol match"
mt5.shutdown()
data={"read_only":True,"account_currency":currency,
      "days_queried":120,"deals_returned":len(deals) if deals is not None else None,
      "summary_by_symbol":summary,"note":note,
      "broker_commission_policy_verified":False,
      "authorization_live":False,"orders_sent":0}
(out/"COMMISSION_HISTORY_COVERAGE.json").write_text(
    json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
print("COMMISSION_HISTORY",json.dumps({"deals_returned":data["deals_returned"],
    "covered_symbols":len(summary),
    "nonzero_fee_symbols":sum(x["commission_deals"]>0 for x in summary.values()),
    "broker_commission_policy_verified":False},ensure_ascii=False))