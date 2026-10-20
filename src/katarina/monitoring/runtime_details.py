from katarina.adapters.demo_permissions import monitor_permission
"""Bounded allowlist of real observation outputs; never invent work or risk clearance."""
import re

def label(value, limit=64):
    return value if isinstance(value, str) and 0 < len(value) <= limit and re.fullmatch(r"[A-Za-z0-9_.:#/-]+", value) else None

def counter(value):
    return value if type(value) is int and 0 <= value <= 1000000 else None

def runtime_details(status, observation, *, fresh):
    """Called only after freshness/safety assessment of the canonical snapshot."""
    rows = []
    if fresh:
        cards = observation.get("symbols")
        if isinstance(cards, dict):
            for symbol, card in list(cards.items())[:17]:
                if not isinstance(card, dict):
                    continue
                method, state = label(card.get("selected_method")), label(card.get("market_state"))
                if (not label(symbol, 40) or not method or not state
                        or card.get("research_only") is not True
                        or card.get("live_execution_authorized") is not False):
                    continue
                rows.append(dict(symbol=symbol, market_state=state, method=method,
                                 action=label(card.get("action")) or "UNKNOWN",
                                 blockers=[b for b in card.get("blocking_reasons", [])[:12]
                                           if label(b, 96)] if isinstance(card.get("blocking_reasons"), list) else []))
    monitor = observation.get("broker_account_monitor")
    monitor = monitor if isinstance(monitor, dict) else {}
    observed = bool(fresh and monitor.get("connected") is True
                    and monitor_permission(monitor)
                    and monitor.get("positions_read_success") is True
                    and monitor.get("orders_read_success") is True
                    and counter(monitor.get("positions_count")) is not None
                    and counter(monitor.get("pending_orders_count")) is not None)
    return dict(snapshot_pid=counter(status.get("pid")),
                heartbeat_utc=status.get("heartbeat_utc") if fresh else None,
                observation_utc=observation.get("observed_at_utc") if fresh else None,
                market_tick_utc=observation.get("market_snapshot_tick_utc") if fresh else None,
                technical_evaluations=rows,
                technical_engine="DETERMINISTIC_CONTEXTUAL_ENGINE",
                account_book_observed=observed,
                positions_count=monitor.get("positions_count") if observed else None,
                pending_orders_count=monitor.get("pending_orders_count") if observed else None,
                risk_clearance=False, language_model_inferred=False)
