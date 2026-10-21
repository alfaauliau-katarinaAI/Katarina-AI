"""Observed broker history coverage without execution or strategy risk clearance.

A finite recent-deal sample is NOT complete lifetime risk, point-in-time
portfolio drawdown, historical fees for the proposed strategy, or a
live-trading budget. No order_send/order_check/order_calc_profit calls.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite


def _finite(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and isfinite(value))


def analyze_deal_coverage(deals, *, current_balance, period_hours=168):
    """Safely summarize observed broker trade DEAL fields without identifiers."""
    result = dict(
        status="HISTORICAL_DEALS_UNAVAILABLE",
        period_hours=period_hours,
        deal_count=None,
        entry_deal_count=None,
        exit_deal_count=None,
        commission_nonzero_samples=None,
        swap_nonzero_samples=None,
        fee_nonzero_samples=None,
        broker_api_money_fields_readable=False,
        net_realized_ratio_to_current_balance=None,
        historical_range_complete=False,
        historical_deal_clock_verified=False,
        realized_daily_loss_verified=False,
        intraday_drawdown_verified=False,
        historical_peak_drawdown_verified=False,
        strategy_specific_costs_verified=False,
        independent_execution_slippage_verified=False,
        current_portfolio_risk_verified=False,
        live_execution_authorized=False,
        orders_submitted=0,
    )
    if deals is None:
        return result
    if not _finite(current_balance) or current_balance <= 0:
        result["status"]="ACCOUNT_BALANCE_UNAVAILABLE"
        return result
    if type(period_hours) is not int or not 1 <= period_hours <= 24 * 30:
        raise ValueError("invalid_deal_history_range")
    entries = exits = commissions = swaps = fees = 0
    cashflow = 0.0
    for deal in deals:
        try:
            kind = int(deal.type)
            entry = int(deal.entry)
            profit = float(deal.profit)
            commission = float(deal.commission)
            swap = float(deal.swap)
            fee = float(deal.fee)
        except (AttributeError, ValueError, TypeError, OverflowError):
            result["status"]="MALFORMED_DEAL_HISTORY"
            return result
        if not all(_finite(x) for x in (profit, commission, swap, fee)):
            result["status"]="MALFORMED_DEAL_HISTORY"
            return result
        # MT5: DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1;
        # ENTRY_IN=0, OUT=1, INOUT=2, OUT_BY=3.
        # A balance credit/deposit is not a trading gain.
        if kind not in (0, 1):
            continue
        if entry not in (0, 1, 2, 3):
            result["status"]="UNKNOWN_TRADE_DEAL_ENTRY"
            return result
        entries += entry == 0
        exits += entry in (1, 2, 3)
        commissions += commission != 0
        swaps += swap != 0
        fees += fee != 0
        cashflow += profit + commission + swap + fee
    result.update(
        status="DEAL_FIELDS_OBSERVED_NOT_FULL_RISK_LEDGER",
        deal_count=entries + exits,
        entry_deal_count=entries,
        exit_deal_count=exits,
        commission_nonzero_samples=commissions,
        swap_nonzero_samples=swaps,
        fee_nonzero_samples=fees,
        broker_api_money_fields_readable=True,
        net_realized_ratio_to_current_balance=round(cashflow/current_balance,8),
    )
    return result


def inspect_history(mt5, *, as_of_utc: datetime, period_hours: int = 168):
    """One bounded read-only MT5 history request; all failures fail closed."""
    if not isinstance(as_of_utc, datetime) or as_of_utc.tzinfo is None:
        raise ValueError("aware_utc_clock_required")
    if type(period_hours) is not int or not 1 <= period_hours <= 24 * 30:
        raise ValueError("invalid_deal_history_range")
    now=as_of_utc.astimezone(timezone.utc)
    result=analyze_deal_coverage(None,current_balance=None,
                                 period_hours=period_hours)
    try:
        account=mt5.account_info()
        if account is None:
            return result
        balance=getattr(account, "balance", None)
        deals=mt5.history_deals_get(now-timedelta(hours=period_hours),now)
        return analyze_deal_coverage(deals,current_balance=balance,
                                     period_hours=period_hours)
    except (AttributeError, OSError, RuntimeError, ValueError, TypeError):
        return result
