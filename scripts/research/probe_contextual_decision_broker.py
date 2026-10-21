"""Read-only KATARINA contextual decision probe against actual broker candles.

Only the *market* part is fetched from MT5. News and prospective outcome
connectors are absent in this diagnostic and therefore passed as UNKNOWN,
so no evidence-backed entry can be authorized. No account queries, writes
or broker orders. Intended to be loaded in memory on a trading-disabled VPS.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json

SYMBOLS=("XAUUSD.vx","EURUSD.vx","NAS100.vx")


def run(symbols):
    import MetaTrader5 as mt5
    from katarina.intelligence.cognition.market_decision import MarketDecisionBrain
    from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle
    from katarina.intelligence.news.news_intelligence import NewsContext
    from katarina.intelligence.cognition.contextual_decision_intelligence import RiskSituation
    from katarina.intelligence.broker.broker_clock_alignment import infer_clock_shift

    if not mt5.initialize():raise RuntimeError("MT5_TERMINAL_UNAVAILABLE")
    try:
        terminal=mt5.terminal_info()
        if terminal is None or terminal.trade_allowed:
            raise RuntimeError("FAIL_CLOSED_TRADING_MUST_BE_DISABLED")
        now=datetime.now(timezone.utc)
        brain=MarketDecisionBrain()
        results=[]
        # The broker's raw rate AND tick epochs can be displaced from UTC.
        # Infer a current common offset across THREE independent live quotes.
        # This is NOT verified historical DST nor authorization for live use.
        quotes={sym:mt5.symbol_info_tick(sym) for sym in symbols}
        shift=infer_clock_shift(
            {sym:int(t.time) for sym,t in quotes.items() if t is not None},
            now.timestamp(),min_symbols=3)
        if not shift.suitable_for_readonly_snapshot:
            print("CONTEXTUAL_BROKER_OBSERVATION",json.dumps({
                "status":"CLOCK_ALIGNMENT_UNVERIFIED",
                "research_only":True,"orders_sent":0,
                "shift_hrs":None,
                "market_snapshots":[{"symbol":s,"decision":"WAIT",
                    "blockers":["broker_clock_alignment_unverified"]} for s in symbols]}))
            return
        seconds_shift=shift.observed_hours_shift*3600
        for sym in symbols:
            spec=mt5.symbol_info(sym)
            tick=quotes.get(sym)
            if spec is None or tick is None:
                results.append({"symbol":sym,"decision":"WAIT",
                                "reasons":["symbol_or_quote_unavailable"]})
                continue
            frames={}
            coverage={}
            for name,tf,seconds in (
                    ("M5",mt5.TIMEFRAME_M5,300),
                    ("M15",mt5.TIMEFRAME_M15,900),
                    ("H1",mt5.TIMEFRAME_H1,3600)):
                raw=mt5.copy_rates_from_pos(sym,tf,1,90)
                if raw is None:
                    frames[name]=[]
                else:
                    frames[name]=[SensorCandle(
                        datetime.fromtimestamp(int(x["time"])-seconds_shift+seconds,timezone.utc),
                        float(x["open"]),float(x["high"]),
                        float(x["low"]),float(x["close"]),
                        float(x["tick_volume"])) for x in raw]
                coverage[name]=len(frames[name])
            spread=max(0.,float(tick.ask)-float(tick.bid))
            quote_age=now.timestamp()-(int(tick.time)-seconds_shift)
            snapshot=RiskSituation(
                system_healthy=True,broker_session_open=bool(spec.trade_mode==4
                  and -15<=quote_age<=300),
                quote_fresh=bool(-15<=quote_age<=300),drawdown_fraction=0.0,
                realized_daily_loss_r=0.0,open_positions=0,
                gross_exposure_fraction=0.0)
            # Neither news nor paper-position risk is verified here.
            # No inventing fresh macro headlines or real trading history.
            news=NewsContext(False,False,0.0,0.0,0,0,
                ("NO_VERIFIED_LIVE_NEWS_OR_ECONOMIC_CALENDAR",))
            result=brain.evaluate_contextually(
                symbol=sym,candles=frames,as_of_utc=now,
                actual_spread=spread,news_context=news,
                macro_evidence=(),resolved_experience=[],
                risk_situation=snapshot)
            results.append(dict(symbol=sym,
                observed_spread_price=round(spread,8),
                quote_age_seconds=round(quote_age,1),
                broker_market_bars=coverage,
                market_state=result.market_state,
                technical_direction=result.conditional_side,
                method=result.selected_method,
                decision=result.action,
                invalidation=result.conditional_invalidation,
                target=result.conditional_target,
                rr_after_spread=result.after_spread_rr_geometry,
                evidence=list(result.confirming_evidence),
                blockers=list(result.blocking_reasons),
                next_condition=result.next_recheck,
                risk_feed_real_account_verified=False,
                news_feed_verified=False,live_authorized=False))
        result={"status":"LIVE_BROKER_MARKET_SNAPSHOT_READ_ONLY",
                "observed_at_utc":now.isoformat(),
                "research_only":True,"orders_sent":0,
                "broker_clock_shift_hours_snapshot_only":shift.observed_hours_shift,
                "clock_confirming_symbols":shift.confirming_symbols,
                "historical_dst_verified":False,
                "news_context":"NOT_CONNECTED",
                "forward_outcome_memory":"NOT_CONNECTED",
                "market_snapshots":results}
        print("CONTEXTUAL_BROKER_OBSERVATION",json.dumps(result,separators=(",",":"),
              allow_nan=False),flush=True)
    finally:
        mt5.shutdown()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--symbols",default=",".join(SYMBOLS))
    args=ap.parse_args()
    symbols=[x.strip() for x in args.symbols.split(",") if x.strip()]
    if not symbols or len(set(symbols))!=len(symbols) or any(s not in SYMBOLS for s in symbols):
        raise ValueError("unsupported_read_only_research_symbol")
    run(symbols)


if __name__=="__main__":
    main()
