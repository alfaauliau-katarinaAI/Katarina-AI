"""WP8b development-only OHLC simulator. Never sends broker orders."""
from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
import math

from katarina.research.dev_dataset import DEV_CUTOFF_UTC
from katarina.research.setups import fibonacci, liquidity_sweep, market_structure, pullback
from katarina.research.setups.core import as_utc, param
from katarina.research.validation import Trade, ValidationError, canonical, sha256_text

METHODS = {
    "fibonacci": fibonacci.detect,
    "liquidity_sweep": liquidity_sweep.detect,
    "market_structure": market_structure.detect,
    "pullback": pullback.detect,
}


def _checked_rows(rows, tf, minutes):
    """Reject invalid archives *before* scanning (never silently drop a bad bar)."""
    if not isinstance(rows, (list, tuple)):
        raise ValidationError("simulation_bars_invalid:" + tf)
    previous = None
    output = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValidationError("simulation_bar_invalid")
        opened = as_utc(row.get("time_utc"))
        closed = as_utc(row.get("closed_at_utc"))
        if opened >= DEV_CUTOFF_UTC or closed > DEV_CUTOFF_UTC:
            raise ValidationError("holdout_data_forbidden")
        if opened + timedelta(minutes=minutes) != closed or (previous is not None and opened <= previous):
            raise ValidationError("simulation_bars_unordered_or_unclosed")
        try:
            op, high, low, close = (float(row[key]) for key in ("open", "high", "low", "close"))
            spread = int(row["spread"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValidationError("simulation_bar_invalid") from exc
        if (not all(math.isfinite(x) and x > 0 for x in (op, high, low, close))
                or low > min(op, close) or high < max(op, close) or high < low
                or type(row["spread"]) is bool or spread < 0 or spread != float(row["spread"])):
            raise ValidationError("simulation_bar_invalid")
        output.append({"time_utc": opened.isoformat(), "closed_at_utc": closed.isoformat(),
                       "open": op, "high": high, "low": low, "close": close, "spread": spread})
        previous = opened
    return output


def _exit(bars, entry_index, stop, target, side, hold):
    """Conservative: invalidation before target on same bar; gaps fill at open when worse."""
    expected_open = as_utc(bars[entry_index]["time_utc"])
    last_index = min(entry_index + hold, len(bars))
    for index in range(entry_index, last_index):
        bar = bars[index]
        opened = as_utc(bar["time_utc"])
        if opened != expected_open:
            return None  # incomplete broker history: never manufacture a trade
        expected_open = as_utc(bar["closed_at_utc"])
        op, lo, hi = bar["open"], bar["low"], bar["high"]
        if side == "BUY":
            if lo <= stop:
                return index, min(op, stop)
            if hi >= target:
                return index, target
        else:
            if hi >= stop:
                return index, max(op, stop)
            if lo <= target:
                return index, target
    if last_index - entry_index < hold:
        return None  # no exit and not enough bars for the declared timeout
    return last_index - 1, bars[last_index - 1]["close"]


def validate_registration(registry, hypothesis_id):
    """Use existing chained registry. Five per symbol+side is a hard research cap."""
    entries = registry.ledger.entries()  # validates chained ledger hash
    grouped = {}
    for entry in entries:
        spec = entry.get("spec", {})
        key = spec.get("symbol"), spec.get("side")
        grouped[key] = grouped.get(key, 0) + 1
        if grouped[key] > 5:
            raise ValidationError("too_many_hypotheses_per_symbol_side")
    entry = registry.get(hypothesis_id)
    if entry is None:
        raise ValidationError("hypothesis_not_registered")
    return entry


def simulate(bars_by_tf, spec, hypothesis_id, *, point: float):
    """Run one registered strategy separately for BUY or SELL, only on verified dev bars.

    Caller must first use load_dev_dataset(), which validates manifest SHA,
    archive SHA and independent historical clock evidence. This pure function
    receives already verified rows and cannot read holdout, broker or network.
    """
    if not isinstance(spec, dict) or spec.get("playbook") not in METHODS:
        raise ValidationError("unsupported_registered_setup")
    side = spec.get("side")
    if side not in ("BUY", "SELL") or not isinstance(hypothesis_id, str) or len(hypothesis_id) != 64:
        raise ValidationError("simulation_spec_invalid")
    if not isinstance(point, (float, int)) or isinstance(point, bool) or not math.isfinite(point) or point <= 0:
        raise ValidationError("simulation_point_invalid")
    params = spec.get("parameters")
    hold = param(params, "max_hold_bars", integer=True, low=1, upper=500)
    n = max(param(params, "lookback", integer=True, low=2) if spec["playbook"] != "fibonacci" else 1,
            param(params, "swing_lookback", integer=True, low=3) if spec["playbook"] == "fibonacci" else 1)
    trend_n = param(params, "trend_lookback", integer=True, low=2)
    m5 = _checked_rows(bars_by_tf.get("M5"), "M5", 5)
    h1 = _checked_rows(bars_by_tf.get("H1"), "H1", 60)
    if not m5 or not h1:
        return []
    results, next_allowed, h1_end = [], None, 0
    method = METHODS[spec["playbook"]]
    for i in range(len(m5) - 1):
        asof = as_utc(m5[i]["closed_at_utc"])
        if next_allowed is not None and asof < next_allowed:
            continue
        if as_utc(m5[i + 1]["time_utc"]) != asof:
            continue
        while h1_end < len(h1) and as_utc(h1[h1_end]["closed_at_utc"]) <= asof:
            h1_end += 1
        if h1_end < trend_n:
            continue
        view = {"M5": m5[max(0, i - n - 1):i + 1],
                "H1": h1[max(0, h1_end - max(n, trend_n) - 1):h1_end]}
        detected = method(view, asof, params, side)
        if not detected:
            continue
        if len(detected) != 1:
            raise ValidationError("multiple_signals_same_bar")
        sig = detected[0]
        if sig.data_until > asof or sig.entry_at != asof or sig.side != side:
            raise ValidationError("simulation_lookahead_or_side")
        entry = m5[i + 1]["open"]  # actual next candle OPEN, not prior signal close
        stop, target = sig.invalidation, sig.target
        if not (stop < entry < target if side == "BUY" else target < entry < stop):
            continue
        outcome = _exit(m5, i + 1, stop, target, side, hold)
        if outcome is None:
            continue  # missing or gapped future: not a closed trade
        j, price = outcome
        exit_at = as_utc(m5[j]["closed_at_utc"])
        if exit_at > DEV_CUTOFF_UTC:
            raise ValidationError("holdout_data_forbidden")
        tid = sha256_text(canonical([hypothesis_id, asof.isoformat(), side]))[:24]
        trade = Trade(trade_id=tid, side=side, entry_at=asof, exit_at=exit_at,
                      known_at=exit_at, data_until=sig.data_until,
                      entry_mid=entry, exit_mid=price, stop_distance=abs(entry - stop),
                      spread_entry=m5[i + 1]["spread"] * point,
                      spread_exit=m5[j]["spread"] * point, trend_side=sig.trend_side)
        results.append(trade)
        next_allowed = exit_at
    return results


def trade_to_dict(trade: Trade):
    output = asdict(trade)
    for key in ("entry_at", "exit_at", "known_at", "data_until"):
        output[key] = output[key].isoformat()
    return output
