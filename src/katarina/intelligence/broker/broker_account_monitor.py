"""Privacy-safe read-only account monitoring for Katarina's observer.

Not an account risk-budget calculator: drawdown, actual costs and net exposure
cannot be certified by a single MT5 account snapshot. Zero order APIs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
import re
from hashlib import sha256
from math import fsum


def _amount_available(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and isfinite(value) and value >= 0)


def inspect_broker_account(mt5, *, observed_at_utc: datetime) -> dict:
    """Inspect only terminal/account/positions/orders (without IDs or balances).

    A missing account/position-book must never be interpreted as zero risk.
    """
    if not isinstance(observed_at_utc, datetime) or observed_at_utc.tzinfo is None:
        raise ValueError("timezone_aware_observation_required")
    result = {
        "source": "MT5_ACCOUNT_TERMINAL_POSITION_ORDER_BOOK_READONLY",
        "observed_at_utc": observed_at_utc.astimezone(timezone.utc).isoformat(),
        "status": "BROKER_ACCOUNT_SNAPSHOT_UNVERIFIED",
        "connected": False,
        "algo_trading_off": False,
        "account_mode": "UNKNOWN",
        "account_financial_fields_available": False,
        "positions_read_success": False,
        "orders_read_success": False,
        "positions_count": None,
        "entry_positions": [],
        "position_snapshot": {"status":"NOT_ATTESTED"},
        "pending_orders_count": None,
        "positions_missing_protective_sl": None,
        "realized_daily_loss_verified": False,
        "historical_peak_drawdown_verified": False,
        "correlated_portfolio_risk_verified": False,
        "broker_fees_and_slippage_verified": False,
        "risk_budget_approved": False,
        "live_execution_authorized": False,
        "orders_submitted": 0,
    }
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        positions = mt5.positions_get()
        orders = mt5.orders_get()
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        return result
    if terminal is None:
        return result
    result["connected"] = bool(getattr(terminal, "connected", False))
    result["algo_trading_off"] = getattr(terminal, "trade_allowed", None) is False
    demo_flag = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
    if account is not None:
        result["account_mode"] = (
            "DEMO" if getattr(account, "trade_mode", None) == demo_flag
            else "OTHER_OR_UNVERIFIED"
        )
        result["account_financial_fields_available"] = (
            _amount_available(getattr(account, "balance", None)) and
            _amount_available(getattr(account, "equity", None)) and
            _amount_available(getattr(account, "margin", None)) and
            _amount_available(getattr(account, "margin_free", None))
        )
    result["demo_observation_enabled"] = (getattr(mt5,"demo_observation_enabled",None) is True
                                           and result["account_mode"] == "DEMO")
    if positions is not None:
        result["positions_read_success"] = True
        result["positions_count"] = len(positions)
        for position in positions[:20]:
            symbol,side,price,epoch=(getattr(position,key,None) for key in ('symbol','type','price_open','time'))
            if (not isinstance(symbol,str) or not re.fullmatch(r'[A-Za-z0-9_.#-]{1,40}',symbol)
                    or type(side) is not int or side not in (0,1)
                    or type(price) not in (int,float) or not isfinite(price) or not 0 < price < 1e12
                    or type(epoch) not in (int,float) or not isfinite(epoch)
                    or not 0 < epoch <= observed_at_utc.timestamp()):
                continue
            result["entry_positions"].append(dict(symbol=symbol,side='BUY' if side==0 else 'SELL',
                entry_price=price,opened_utc=datetime.fromtimestamp(epoch,timezone.utc).isoformat()))
        result["positions_missing_protective_sl"] = sum(
            not (isinstance(getattr(p, "sl", None), (int, float))
                 and isfinite(getattr(p, "sl", float("nan")))
                 and getattr(p, "sl") > 0)
            for p in positions
        )
    # Explicitly requested display metrics. Never publish account IDs, balances or tickets.
    currency=getattr(account,'currency',None) if account is not None else None
    if (result['connected'] and positions is not None and len(positions)<=10000
            and isinstance(currency,str) and re.fullmatch(r'[A-Z][A-Z0-9]{2,7}',currency)):
        rows=[];totals=[];complete=True
        for p in positions:
            profit,swap=getattr(p,'profit',None),getattr(p,'swap',None)
            valid_amount=lambda v:type(v) in (int,float) and isfinite(v) and abs(v)<1e12
            if not valid_amount(profit) or not valid_amount(swap):complete=False
            else:totals.append(profit+swap)
            symbol,side,price,epoch=(getattr(p,k,None) for k in ('symbol','type','price_open','time'))
            ticket=getattr(p,'ticket',None)
            if (not isinstance(symbol,str) or not re.fullmatch(r'[A-Za-z0-9_.#-]{1,40}',symbol)
                    or type(side) is not int or side not in (0,1) or type(ticket) is not int or ticket<=0
                    or not valid_amount(price) or price<=0 or type(epoch) not in (int,float)
                    or not isfinite(epoch) or epoch<=0):
                continue
            row=dict(id=sha256(('position:'+str(ticket)).encode()).hexdigest()[:24],symbol=symbol,
                     side='BUY' if side==0 else 'SELL',entry_price=price,
                     opened_utc=datetime.fromtimestamp(epoch,timezone.utc).isoformat() if epoch<=observed_at_utc.timestamp() else None,
                     profit=profit if valid_amount(profit) else None,swap=swap if valid_amount(swap) else None,
                     floating=profit+swap if valid_amount(profit) and valid_amount(swap) else None)
            for key,attr in [('current_price','price_current'),('stop_loss','sl'),('take_profit','tp')]:
                value=getattr(p,attr,None);row[key]=value if valid_amount(value) and value>=0 else None
            if len(rows)<100:rows.append(row)
        binding=sha256((str(account.login)+'|'+account.server).encode()).hexdigest() if type(getattr(account,'login',None)) is int and isinstance(getattr(account,'server',None),str) else None
        result['position_snapshot']=dict(status='OBSERVED',as_of_utc=result['observed_at_utc'],currency=currency,private_account_binding=binding,
            mode=result['account_mode'],positions=rows,total_count=len(positions),truncated=len(rows)<len(positions),
            floating_total=fsum(totals) if complete else None,
            pnl_basis='PROFIT_PLUS_SWAP_EXCLUDES_OPEN_COMMISSION')
    if orders is not None:
        result["orders_read_success"] = True
        result["pending_orders_count"] = len(orders)
    from katarina.adapters.demo_permissions import monitor_permission
    if (result["connected"] and monitor_permission(result) and
            result["account_financial_fields_available"] and
            result["positions_read_success"] and
            result["orders_read_success"]):
        result["status"] = ("READONLY_ACCOUNT_OBSERVED_NO_RISK_CLEARANCE" if result["algo_trading_off"]
                            else "DEMO_ACCOUNT_OBSERVED_NO_RISK_CLEARANCE")
    else:
        result["status"] = "BROKER_ACCOUNT_SNAPSHOT_DEGRADED"
    return result
