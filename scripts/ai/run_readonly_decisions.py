"""Read-only periodic seven-market observer. No order_send or live trading.

Requires terminal session and repo PYTHONPATH. Reports may identify regimes,
but news context is NOT VERIFIED, so all recommendations fail closed to WAIT.
"""
from __future__ import annotations
import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
from smoke_closed_market_decision import SYMBOLS, TFS, candles_for
from katarina.intelligence.cognition.market_decision_pipeline import MarketDecisionPipeline
from katarina.intelligence.broker.broker_clock_alignment import infer_clock_shift
from katarina.intelligence.broker.causal_broker_quotes import server_epoch_to_utc

OUT = Path(r"C:\KatarinaDev\artifacts\decision-observer")
TERMINAL = r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe"


def publish(data):
    OUT.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(data, indent=2, allow_nan=False) + "\n").encode("utf-8")
    temp, target = OUT / "latest.tmp", OUT / "latest.json"
    temp.write_bytes(payload)
    try:
        temp.replace(target)
    except PermissionError:
        # The legacy latest.json may have protected ACLs or be locked by the
        # website. Never weaken its ACL or overwrite another owner's file.
        try:
            with target.open("r+b") as file:
                file.seek(0)
                file.write(payload)
                file.truncate()
                file.flush()
                os.fsync(file.fileno())
            temp.unlink(missing_ok=True)
        except PermissionError:
            try:
                temp.replace(OUT / "latest-explainable.json")
            except PermissionError:
                snapshot = OUT / ("explainable-" +
                    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
                snapshot.write_bytes(payload)
                temp.unlink(missing_ok=True)


def main():
    now = datetime.now(timezone.utc)
    report = dict(mode="read_only_no_orders_no_walkforward",
                  as_of_utc=now.isoformat(),
                  news_context_verified=False,
                  live_execution_authorized=False,
                  decision_model="EXPLAINABLE_MARKET_DECISION_V1",
                  symbols={})
    if not mt5.initialize(path=TERMINAL):
        report["error"] = "mt5_connection_failed"
        publish(report)
        print("MARKET_OBSERVER: connection_failed")
        return 2
    try:
        observer = MarketDecisionPipeline()
        snapshot_ticks = {symbol: mt5.symbol_info_tick(symbol) for symbol in SYMBOLS}
        finding = infer_clock_shift(
            {symbol: int(tick.time) for symbol, tick in snapshot_ticks.items() if tick},
            now.timestamp(),
        )
        # Legacy observer cannot certify broker bar history across DST.
        # Keep its outputs diagnostic-only and fail closed when clock is unknown.
        shift = finding.observed_hours_shift if finding.suitable_for_readonly_snapshot else None
        for symbol in SYMBOLS:
            try:
                info = mt5.symbol_info(symbol)
                if info is None:
                    raise ValueError("symbol_spec_missing")
                bars = candles_for(symbol)
                bars = {k: [r for r in b if r.closed_at_utc <= now] for k, b in bars.items()}
                fresh = all(
                    len(bars[k]) >= 55 and
                    timedelta(0) <= now - bars[k][-1].closed_at_utc <= timedelta(minutes=mins * 2)
                    for k, (_, mins) in TFS.items()
                )
                tick = snapshot_ticks[symbol]
                valid_quote = (tick is not None and tick.bid > 0 and tick.ask >= tick.bid)
                tick_age = (now.timestamp() - server_epoch_to_utc(
                    tick.time_msc / 1000, shift)) if valid_quote and shift is not None else None
                quote_fresh = tick_age is not None and 0 <= tick_age <= 180
                # Clock basis for candle history is not independently verified.
                open_for_research = False
                spread = float(tick.ask - tick.bid) if valid_quote else float("nan")
                read = observer.evaluate(
                    symbol=symbol, candles=bars, as_of_utc=now,
                    actual_spread=spread, broker_session_open=open_for_research,
                    data_fresh=fresh, news_blackout=False,
                    news_context_verified=False,
                    use_structural_entry_gate=True,
                    use_semantic_setup_gate=True,
                    instrument_point=float(info.point))
                report["symbols"][symbol] = {
                    "closed_M5_utc": bars["M5"][-1].closed_at_utc.isoformat(),
                    "regime": read.market_state, "playbook": read.playbook,
                    "action": read.action, "reasons": read.reasons,
                    "tools": read.tools,
                    "decision_detail": (
                        asdict(read.decision_detail)
                        if read.decision_detail is not None else None
                    ),
                    "entry_quality": (
                        asdict(read.entry_quality)
                        if read.entry_quality is not None else None
                    ),
                    "semantic_setup": asdict(read.semantic_setup) if read.semantic_setup else None,
                    "experimental_exit_plan": (
                        asdict(read.experimental_exit_plan)
                        if read.experimental_exit_plan is not None else None
                    ),
                    "market_data_fresh": fresh,
                    "quote_fresh": quote_fresh,
                    "broker_clock_verified_current_only": shift is not None,
                    "bar_history_clock_verified": False,
                    "live_execution_authorized": False,
                }
            except (RuntimeError, ValueError, TypeError, IndexError) as exc:
                report["symbols"][symbol] = {
                    "regime": "UNKNOWN", "action": "WAIT",
                    "error": type(exc).__name__ + ":" + str(exc)}
    finally:
        mt5.shutdown()
    report["symbols_scanned"] = len(report["symbols"])
    report["symbols_failed"] = sum(
        "error" in item for item in report["symbols"].values())
    publish(report)
    print("MARKET_OBSERVER: saved", report["symbols_scanned"],
          "failed", report["symbols_failed"],
          "at", report["as_of_utc"], "orders=0")
    return 0 if report["symbols_scanned"] == len(SYMBOLS) and not report["symbols_failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())