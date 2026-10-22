"""Bounded full-broker discovery INSIDE the canonical read-only observer.

This is an exploratory, quote/M1-cost research screen, not a trade setup,
validated strategy, Stage-0 tick observation, or execution authorization.
The existing continuous lab keeps a persistent fair rotation across all
trade-enabled broker symbols. It never manufactures a missing broker symbol.
"""
from __future__ import annotations

from datetime import datetime
from math import isfinite
from statistics import median

from katarina.intelligence.lab.continuous_research_lab import (
    catalog_symbols, select_batch,
)


def discover_quote_batch(mt5, db, catalog, now: datetime, *,
                         clock_shift_hours: float, budget: int = 12,
                         deep_symbols=()) -> dict:
    """Survey a bounded batch; every eligible broker symbol gets a turn.

    Deep multi-timeframe analysis and the Stage-0 observation ledger continue
    independently on their existing symbols and evidence requirements.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("discovery_requires_aware_clock")
    if not isinstance(budget, int) or isinstance(budget, bool) or not 1 <= budget <= 24:
        raise ValueError("invalid_discovery_budget")
    if not isfinite(clock_shift_hours) or abs(clock_shift_hours) > 14:
        raise ValueError("invalid_broker_clock_shift")
    if catalog is None:
        raise ValueError("broker_catalog_unavailable")

    universe = catalog_symbols(catalog)
    if not universe:
        return dict(status="NO_TRADE_ENABLED_MARKETS", universe_size=0,
                    surveyed=0, observed_symbols=[], research_priority=[],
                    entries_authorized=0, orders_submitted=0)
    names = select_batch(db, catalog, min(budget, len(universe)), now)
    sampled = []
    for name in names:
        row = {"symbol": name, "state": "WAIT", "reasons": [],
               "spread_price": None, "spread_to_m1_range": None}
        try:
            if not mt5.symbol_select(name, True):
                row["reasons"].append("broker_symbol_select_failed")
            else:
                tick = mt5.symbol_info_tick(name)
                if tick is None:
                    row["reasons"].append("broker_tick_missing")
                else:
                    bid, ask = float(tick.bid), float(tick.ask)
                    epoch = float(getattr(tick, "time_msc", 0) or 0) / 1000
                    if not epoch:
                        epoch = float(getattr(tick, "time", 0) or 0)
                    age = now.timestamp() - (epoch - clock_shift_hours * 3600)
                    if not (isfinite(bid) and isfinite(ask) and 0 < bid <= ask):
                        row["reasons"].append("invalid_bid_ask")
                    elif not (isfinite(age) and -5 <= age <= 180):
                        row["reasons"].append("stale_or_future_broker_quote")
                    else:
                        row["spread_price"] = round(ask - bid, 10)
                        row["quote_age_seconds"] = round(age, 2)
                        rates = mt5.copy_rates_from_pos(
                            name, mt5.TIMEFRAME_M1, 1, 24)
                        if rates is None:
                            row["reasons"].append("closed_m1_bars_unavailable")
                        else:
                            ranges = []
                            for bar in rates:
                                width = float(bar["high"]) - float(bar["low"])
                                if isfinite(width) and width > 0:
                                    ranges.append(width)
                            if len(ranges) < 16:
                                row["reasons"].append("insufficient_closed_m1_ranges")
                            else:
                                row["spread_to_m1_range"] = round(
                                    (ask - bid) / median(ranges), 6)
        except (AttributeError, KeyError, ValueError, TypeError, OverflowError):
            row["reasons"].append("invalid_broker_discovery_evidence")
        except Exception:
            # A broker API failure must never bring down the canonical observer.
            row["reasons"].append("broker_discovery_unavailable")
        sampled.append(row)

    eligible = sorted(
        (r for r in sampled if not r["reasons"]
         and r["spread_to_m1_range"] is not None),
        key=lambda r: (r["spread_to_m1_range"], r["symbol"]),
    )
    return {
        "status": "EXPLORATORY_NO_TRADING_AUTHORITY",
        "universe_size": len(universe),
        "surveyed": len(sampled),
        "observed_symbols": list(deep_symbols),
        "sampled": sampled,
        "research_priority": [r["symbol"] for r in eligible[:5]],
        "priority_basis": "DESCRIPTIVE_SPREAD_VS_CLOSED_M1_RANGE_NOT_SETUP_SCORE",
        "coverage": "PERSISTENT_ROUND_ROBIN_QUOTE_SCREEN_NOT_STAGE0_SNAPSHOT",
        "entries_authorized": 0,
        "orders_submitted": 0,
    }
