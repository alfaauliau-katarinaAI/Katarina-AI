"""Safe MT5 quote/contract observation; never issues trade or account mutations.

This is a single-time snapshot, not an execution preflight, backtest,
forward-test pass, or evidence of profitable/authorized trading. No account
number, server, balance, equity, or credentials are emitted.

Run (using an existing MT5-connected Python environment)::
    PYTHONPATH=src python scripts/mt5/audit_readonly_quotes.py --max-age-seconds 180

Production observation deliberately uses bounded historical UTC Bid/Ask ticks;
raw terminal tick timestamps can be broker-local and appear hours in the
future. Historical ticks are quote provenance, NOT witnessed trade fills.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import time
from types import SimpleNamespace
from typing import Any

DEFAULT_SYMBOLS = (
    "XAUUSD.vx", "EURUSD.vx", "GBPUSD.vx", "USDJPY.vx",
    "NAS100.vx", "US30.vx", "JPN225.vx",
)


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def quote_snapshot(symbol: str, info: Any, tick: Any, *, now_ms: int,
                   max_age_ms: int) -> dict[str, Any]:
    """Examine only observable quotes. Unknown, stale, or future => WAIT."""
    item: dict[str, Any] = {"symbol": symbol, "decision": "WAIT"}
    if info is None:
        item["reason"] = "symbol_metadata_unavailable"
        return item
    item["contract_size"] = _number(getattr(info, "trade_contract_size", None))
    item["tick_size"] = _number(getattr(info, "trade_tick_size", None))
    item["minimum_lot"] = _number(getattr(info, "volume_min", None))
    item["lot_step"] = _number(getattr(info, "volume_step", None))
    if tick is None:
        item["reason"] = "quote_unavailable"
        return item
    bid = _number(getattr(tick, "bid", None))
    ask = _number(getattr(tick, "ask", None))
    try:
        tick_ms = int(getattr(tick, "time_msc"))
    except (TypeError, ValueError, OverflowError, AttributeError):
        item["reason"] = "invalid_quote_timestamp"
        return item
    if not tick_ms or bid is None or ask is None or bid <= 0 or ask < bid:
        item["reason"] = "invalid_bid_ask_or_timestamp"
        return item
    age_ms = now_ms - tick_ms
    try:
        item["quote_utc"] = datetime.fromtimestamp(tick_ms / 1000, timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        item["reason"] = "invalid_quote_timestamp"
        return item
    item["quote_age_seconds"] = round(age_ms / 1000, 3)
    item["spread_points"] = None
    point = _number(getattr(info, "point", None))
    if point is not None and point > 0:
        item["spread_points"] = round((ask - bid) / point, 3)
    if age_ms < -2000:
        item["reason"] = "future_dated_quote"
    elif age_ms > max_age_ms:
        item["reason"] = "stale_quote"
    elif (item["contract_size"] is None or item["contract_size"] <= 0
          or item["tick_size"] is None or item["tick_size"] <= 0
          or item["minimum_lot"] is None or item["minimum_lot"] <= 0
          or item["lot_step"] is None or item["lot_step"] <= 0):
        item["reason"] = "invalid_broker_contract_spec"
    else:
        item["decision"] = "OBSERVED_ONLY"
        item["reason"] = "fresh_quote_and_spec_observed"
    return item


def observe(mt5: Any, *, symbols: tuple[str, ...], now_ms: int,
            max_age_ms: int, terminal_path: str | None = None,
            historical_quote_reader: Any = None) -> dict[str, Any]:
    """Only invokes read-only MetaTrader5 APIs; does not select symbols."""
    result: dict[str, Any] = {
        "proof_type": "KATARINA_MT5_READ_ONLY_QUOTE_SNAPSHOT",
        "schema_version": 1,
        "observed_utc": datetime.fromtimestamp(now_ms / 1000, timezone.utc).isoformat(),
        "broker_mutation": False,
        "live_execution_enabled": False,
        "live_risk_ready": False,
        "strategy_validated": False,
        "result": "WAIT_INSUFFICIENT_BROKER_EVIDENCE",
        "quotes": [],
    }
    if not symbols or len(set(symbols)) != len(symbols):
        result["reason"] = "invalid_symbol_selection"
        return result
    connected = False
    try:
        kwargs: dict[str, Any] = {"timeout": 10000}
        if terminal_path:
            kwargs["path"] = terminal_path
        if not mt5.initialize(**kwargs):
            result["reason"] = "mt5_initialize_failed"
            return result
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        connected = bool(terminal is not None and getattr(terminal, "connected", False))
        result["terminal_connected"] = connected
        result["account_available"] = account is not None
        # Do not emit account login, server, leverage, balance, equity, or positions.
        if account is not None:
            mode = getattr(account, "trade_mode", None)
            if mode == getattr(mt5, "ACCOUNT_TRADE_MODE_REAL", -101):
                result["account_mode"] = "real"
            elif mode == getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", -102):
                result["account_mode"] = "demo"
            elif mode == getattr(mt5, "ACCOUNT_TRADE_MODE_CONTEST", -103):
                result["account_mode"] = "contest"
            else:
                result["account_mode"] = "unknown"
            currency = getattr(account, "currency", "")
            result["account_denomination"] = ("USC" if str(currency).upper() == "USC"
                                              else "USD" if str(currency).upper() == "USD"
                                              else "UNVERIFIED_OTHER")
        if not connected or account is None:
            result["reason"] = "terminal_disconnected_or_account_unavailable"
            return result
        for symbol in symbols:
            info = mt5.symbol_info(symbol)
            source = "RAW_TERMINAL_TIMESTAMP_DIAGNOSTIC"
            if historical_quote_reader is not None:
                source = "MT5_HISTORICAL_UTC_BID_ASK_READONLY"
                historical = (historical_quote_reader(
                    mt5, symbol, datetime.fromtimestamp(now_ms / 1000, timezone.utc),
                    lookback_seconds=max_age_ms / 1000)
                    if info is not None else None)
                # The existing causal reader returns (bid, ask, UTC epoch sec).
                # Never fall back to broker-local raw timestamps on failure.
                tick = (SimpleNamespace(bid=historical[0], ask=historical[1],
                                        time_msc=int(historical[2] * 1000))
                        if historical is not None else None)
            else:
                tick = mt5.symbol_info_tick(symbol) if info is not None else None
            item = quote_snapshot(symbol, info, tick, now_ms=now_ms,
                                  max_age_ms=max_age_ms)
            item["quote_source"] = source
            result["quotes"].append(item)
        if all(q["decision"] == "OBSERVED_ONLY" for q in result["quotes"]):
            result["result"] = "PASS_SINGLE_READ_ONLY_OBSERVATION"
            result["reason"] = "all_requested_quotes_fresh_not_forward_validation"
        else:
            result["reason"] = "one_or_more_symbols_wait"
        return result
    except Exception:
        # Do not leak a broker or account identifier via exception strings.
        result["result"] = "WAIT_INSUFFICIENT_BROKER_EVIDENCE"
        result["reason"] = "mt5_read_exception"
        return result
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal-path", default=None)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--max-age-seconds", type=int, default=180)
    args = parser.parse_args()
    if not 0 < args.max_age_seconds <= 180 or not args.symbols or len(set(args.symbols)) != len(args.symbols):
        parser.error("Quote age must be 1..180 seconds with distinct, nonempty symbols")
    try:
        import MetaTrader5 as mt5
        from katarina.intelligence.broker.causal_broker_quotes import last_past_quote
    except ImportError:
        print(json.dumps({"result": "WAIT_INSUFFICIENT_BROKER_EVIDENCE",
                          "reason": "MT5_or_causal_UTC_quote_reader_unavailable",
                          "live_execution_enabled": False}))
        return 2
    output = observe(mt5, symbols=tuple(args.symbols),
                     now_ms=time.time_ns() // 1_000_000,
                     max_age_ms=args.max_age_seconds * 1000,
                     terminal_path=args.terminal_path,
                     historical_quote_reader=last_past_quote)
    print(json.dumps(output, sort_keys=True, allow_nan=False))
    return 0 if output["result"] == "PASS_SINGLE_READ_ONLY_OBSERVATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
