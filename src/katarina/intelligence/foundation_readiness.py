"""Single-observer foundation diagnostics. No trading or strategy selection.

Separate software/observation health from independent learning, broker-cost
validation, multi-asset risk clearance and any eventual trade authorization.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite


def _clock(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def assess_foundation(report: dict, *, expected_symbols: int = 17) -> dict:
    """Return an auditable, honest status for an existing observer cycle."""
    if (not isinstance(report, dict) or type(expected_symbols) is not int or
            not 1 <= expected_symbols <= 17):
        raise ValueError("invalid_foundation_input")
    entries = report.get("symbols")
    entries = entries if isinstance(entries, dict) else {}
    obs = _clock(report.get("observed_at_utc"))
    tick = _clock(report.get("market_snapshot_tick_utc"))
    timeref = report.get("time_reference") or {}
    cognition = report.get("unified_cognitive_cycle") or {}
    monitor = report.get("broker_account_monitor") or {}
    history = report.get("broker_history_coverage") or {}
    official_cache = report.get("official_cache_integrity") or {}
    feed = report.get("news_feed_status") or {}
    final = report.get("final_actions") or {}
    shadow = report.get("virtual_shadow_summary") or {}
    counts = shadow.get("counts") or {}
    broker_clock_ok = (
        timeref.get("canonical_market_clock") ==
        "MT5_COPY_TICKS_RANGE_TIME_MSC_UTC"
        and timeref.get("historical_dst_verified") is False
        and isinstance(timeref.get("confirming_symbols"), int)
        and timeref["confirming_symbols"] >= min(expected_symbols, 5)
    )
    clock_ok = bool(obs and tick and 0 <= (obs-tick).total_seconds() <= 120
                    and broker_clock_ok)
    errors = {
        symbol: info.get("blocking_reasons", [])
        for symbol, info in entries.items()
        if not isinstance(info, dict) or any(
            isinstance(x, str) and x.startswith("sensor_error:")
            for x in (info.get("blocking_reasons") or [])
        )
    }
    news_transport_ready = (
        all(feed.get(k) in ("OK", "CACHED")
            for k in ("fed", "ecb", "boe", "calendar"))
    )
    signals_total = (
        sum(v for v in final.values() if type(v) is int and v >= 0)
        if isinstance(final, dict) else -1
    )
    engineering = {
        "read_only_terminal_confirmed": (
            monitor.get("connected") is True and
            monitor.get("algo_trading_off") is True
        ),
        "account_position_order_book_readable": (
            monitor.get("status") ==
            "READONLY_ACCOUNT_OBSERVED_NO_RISK_CLEARANCE"
            or (monitor.get("status")=="DEMO_ACCOUNT_OBSERVED_NO_RISK_CLEARANCE"
                and monitor.get("demo_observation_enabled") is True and monitor.get("account_mode")=="DEMO")
        ),
        "canonical_utc_market_clock": clock_ok,
        "no_unprotected_broker_positions": (
            monitor.get("positions_read_success") is True and
            monitor.get("positions_missing_protective_sl") == 0
        ),
        "expected_symbols_observed": (
            report.get("observed_symbols") == expected_symbols and
            len(entries) == expected_symbols and
            signals_total == expected_symbols
        ),
        "sensors_without_errors": len(errors) == 0 and len(entries) > 0,
        "official_news_cache_transport_reachable": news_transport_ready,
        "official_source_cache_digest_and_freshness": (
            official_cache.get("all_four_cache_digests_fresh") is True and
            official_cache.get("policy_inference_from_headlines_authorized") is False
        ),
        "recent_broker_deal_book_readable": (
            history.get("status") ==
            "DEAL_FIELDS_OBSERVED_NOT_FULL_RISK_LEDGER" and
            history.get("historical_range_complete") is False and
            history.get("live_execution_authorized") is False
        ),
        "unified_memory_checkpoint_matches": (
            cognition.get("source_snapshot_matches_active") is True and
            cognition.get("real_execution_authorized") is False
        ),
        "single_virtual_portfolio_limit": (
            type(counts.get("OPEN", 0)) is int and
            0 <= counts.get("OPEN", 0) <= 1
        ),
        "zero_live_order_authority": (
            report.get("orders_submitted") == 0 and
            report.get("live_execution_authorized") is False and
            report.get("production_execution") is False
        ),
    }
    # Deliberately explicit: these cannot be inferred from a snapshot,
    # including when account positions are zero.
    unavailable = [
        "independently_verified_real_broker_trade_outcomes",
        "commission_slippage_swap_reconciliation",
        "correlated_portfolio_risk_and_daily_loss_history",
        "point_in_time_approved_macro_trade_evidence",
        "independent_out_of_sample_strategy_proof",
        "owner_approved_live_execution",
    ]
    explicit_demo=(monitor.get("demo_observation_enabled") is True and monitor.get("account_mode")=="DEMO")
    bad = [name for name, ok in engineering.items() if not ok
           and not (name=="read_only_terminal_confirmed" and explicit_demo)]
    # News transport can degrade without invalidating the market and
    # cognition history, but is NEVER a permission to fabricate news.
    status = ("RESEARCH_FOUNDATION_PASS_PRODUCTION_BLOCKED" if not bad
              else "RESEARCH_FOUNDATION_DEGRADED_PRODUCTION_BLOCKED")
    return {
        "schema": 1,
        "status": status,
        "engineering_checks": engineering,
        "engineering_failure_reasons": bad,
        "sensor_errors_by_symbol": errors,
        "technical_symbol_count": len(entries),
        "news_transport_is_not_verified_trading_news": True,
        "account_snapshot_is_not_risk_clearance": True,
        "deal_book_is_not_daily_loss_or_drawdown_clearance": True,
        "cognitive_history_is_not_live_trade_experience": True,
        "unknown_or_unverified_production_gates": unavailable,
        "knowledge_matured_virtual_observations": (
            cognition.get("matured_observations")
            if type(cognition.get("matured_observations")) is int else None
        ),
        "market_clock_source": timeref.get("canonical_market_clock"),
        "live_execution_authorized": False,
        "orders_submitted": 0,
    }
