"""Read-only MT5 closed-bar smoke check. No order_send, no strategy backtest.

Run with PYTHONPATH pointing to repository src. Historical decision is a single
archived market-state inspection, NOT walk-forward or proof of edge.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5
from katarina.intelligence.cognition.market_decision_pipeline import (
    MarketDecisionPipeline, SensorCandle,
)

TFS = {"M5": (mt5.TIMEFRAME_M5, 5),
       "M15": (mt5.TIMEFRAME_M15, 15),
       "H1": (mt5.TIMEFRAME_H1, 60)}
SYMBOLS = ("XAUUSD.vx", "EURUSD.vx", "GBPUSD.vx", "USDJPY.vx",
           "NAS100.vx", "US30.vx", "JPN225.vx")


def candles_for(symbol: str):
    out = {}
    for name, (period, mins) in TFS.items():
        rows = mt5.copy_rates_from_pos(symbol, period, 1, 140)
        if rows is None or len(rows) < 55:
            raise RuntimeError("insufficient_MT5_" + name)
        out[name] = [
            SensorCandle(
                datetime.fromtimestamp(int(r["time"]), timezone.utc)
                + timedelta(minutes=mins),
                float(r["open"]), float(r["high"]), float(r["low"]),
                float(r["close"]), float(r["tick_volume"]))
            for r in rows
        ]
    return out


def main():
    if not mt5.initialize():
        print(json.dumps({"connected": False, "reason": str(mt5.last_error())}))
        return 2
    try:
        client = MarketDecisionPipeline()
        results = []
        for symbol in SYMBOLS:
            try:
                info = mt5.symbol_info(symbol)
                if info is None:
                    raise RuntimeError("symbol_not_found")
                readings = candles_for(symbol)
                # Match a valid closed-bar cutoff; no lookahead across timeframes.
                anchor = readings["M5"][-1].closed_at_utc
                readings = {k: [r for r in v if r.closed_at_utc <= anchor]
                            for k, v in readings.items()}
                # This is a historical single-snapshot demonstration (session
                # simulated open) and never authorizes a broker order.
                # Pull the broker's archived Bid/Ask just BEFORE the signal
                # cutoff. Never substitute a Sunday/current or zero spread.
                ticks = mt5.copy_ticks_range(
                    symbol, anchor - timedelta(minutes=5),
                    anchor, mt5.COPY_TICKS_INFO)
                if ticks is None or len(ticks) == 0:
                    raise RuntimeError("historical_bid_ask_missing")
                last = ticks[-1]
                tick_time = datetime.fromtimestamp(
                    int(last["time"]), timezone.utc)
                if (anchor - tick_time > timedelta(minutes=5) or
                    float(last["bid"]) <= 0 or
                    float(last["ask"]) < float(last["bid"])):
                    raise RuntimeError("historical_bid_ask_invalid")
                spread = float(last["ask"] - last["bid"])
                historical = client.evaluate(
                    symbol=symbol, candles=readings, as_of_utc=anchor,
                    actual_spread=spread, broker_session_open=True,
                    data_fresh=True, news_blackout=False)
                # Current day session is not assumed open; no trade is possible.
                present = client.evaluate(
                    symbol=symbol, candles=readings,
                    as_of_utc=datetime.now(timezone.utc),
                    actual_spread=spread, broker_session_open=False,
                    data_fresh=False, news_blackout=False)
                results.append({
                    "symbol": symbol, "closed_at_utc": anchor.isoformat(),
                    "historical_snapshot_state": historical.market_state,
                    "historical_snapshot_playbook": historical.playbook,
                    "historical_snapshot_hypothetical_action": historical.action,
                    "historical_snapshot_reason": historical.reasons[:3],
                    "present_action": present.action,
                    "present_reason": present.reasons[-1:],
                    "tick_volume_vwap_available": (
                        historical.tools.get("broker_tick_volume_vwap") is not None),
                    "real_orders_sent": 0,
                    "live_authorized": historical.live_execution_authorized,
                })
            except (RuntimeError, ValueError, TypeError) as exc:
                results.append({"symbol": symbol, "error": str(exc)})
        print(json.dumps({"source": "MT5_closed_bars_readonly",
                          "mode": "functional_sensor_smoke_not_walkforward",
                          "connected": True, "results": results}, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
