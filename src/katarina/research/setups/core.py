"""Shared causal guards for WP8b development-only research.

Detectors read *closed* development bars only. Their entry_mid is a signal
estimate (last closed M5 close), not an executable fill; the future simulator
must substitute the next bar's actual open and observed costs.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

from katarina.research.dev_dataset import DEV_CUTOFF_UTC
from katarina.research.validation import ValidationError


@dataclass(frozen=True)
class Signal:
    setup: str
    side: str
    entry_at: datetime
    entry_mid: float
    invalidation: float
    target: float
    data_until: datetime
    trend_side: str
    regime: str

    def __post_init__(self):
        if self.side not in ("BUY", "SELL"):
            raise ValidationError("setup_side_invalid")
        if self.data_until > self.entry_at or self.entry_at >= DEV_CUTOFF_UTC:
            raise ValidationError("holdout_data_forbidden")
        if not all(math.isfinite(x) and x > 0 for x in
                   (self.entry_mid, self.invalidation, self.target)):
            raise ValidationError("setup_price_invalid")
        if ((self.side == "BUY" and not self.invalidation < self.entry_mid < self.target)
                or (self.side == "SELL" and not self.target < self.entry_mid < self.invalidation)):
            raise ValidationError("setup_geometry_invalid")


def checked_side(side: str) -> None:
    if side not in ("BUY", "SELL"):
        raise ValidationError("setup_side_invalid")


def as_utc(value) -> datetime:
    try:
        out = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if out.tzinfo is None:
            raise ValueError("naive")
        out = out.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValidationError("setup_timestamp_invalid") from error
    return out


def param(params, name: str, *, integer: bool = False, low: float = 0, upper=None):
    if not isinstance(params, dict) or name not in params:
        raise ValidationError("setup_parameter_required:" + name)
    v = params[name]
    if integer:
        if type(v) is not int:
            raise ValidationError("setup_parameter_integer:" + name)
    elif isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValidationError("setup_parameter_number:" + name)
    v = float(v)
    if not math.isfinite(v) or v < low or (upper is not None and v > upper):
        raise ValidationError("setup_parameter_range:" + name)
    return int(v) if integer else v


def closed_bars(bars_by_tf, tf: str, as_of, count: int, minutes: int):
    """Only inspect OHLC of rows whose closed_at_utc <= as_of.

    Future bar OHLC values are deliberately not read at all. Includes strict
    ordering and close-time checks to avoid synthetic look-ahead.
    """
    if not isinstance(bars_by_tf, dict) or tf not in bars_by_tf:
        raise ValidationError("setup_timeframe_missing:" + tf)
    point = as_utc(as_of)
    if point >= DEV_CUTOFF_UTC:
        raise ValidationError("holdout_data_forbidden")
    if count < 1:
        raise ValidationError("setup_count_invalid")
    out = deque(maxlen=count)
    previous = None
    for row in bars_by_tf[tf]:
        if not isinstance(row, dict):
            raise ValidationError("setup_bar_invalid")
        stamp = as_utc(row.get("closed_at_utc"))
        if stamp > point:
            continue
        if stamp > DEV_CUTOFF_UTC:
            raise ValidationError("holdout_data_forbidden")
        opened = as_utc(row.get("time_utc"))
        if opened + timedelta(minutes=minutes) != stamp:
            raise ValidationError("setup_bar_interval_invalid")
        if previous is not None and stamp <= previous:
            raise ValidationError("setup_bars_unordered")
        previous = stamp
        try:
            op, hi, lo, cl = (float(row[k]) for k in ("open", "high", "low", "close"))
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValidationError("setup_ohlc_invalid") from error
        if not all(math.isfinite(x) and x > 0 for x in (op, hi, lo, cl)):
            raise ValidationError("setup_ohlc_invalid")
        if lo > min(op, cl) or hi < max(op, cl) or hi < lo:
            raise ValidationError("setup_ohlc_invalid")
        out.append({"open": op, "high": hi, "low": lo, "close": cl, "closed": stamp})
    return list(out)


def trend(bars_by_tf, as_of, params):
    n = param(params, "trend_lookback", integer=True, low=2)
    h1 = closed_bars(bars_by_tf, "H1", as_of, n, 60)
    if len(h1) < n:
        return "FLAT", "RANGE"
    last, first = h1[-1]["close"], h1[0]["close"]
    if last > first:
        return "BUY", "UPTREND"
    if last < first:
        return "SELL", "DOWNTREND"
    return "FLAT", "RANGE"


def signal(setup: str, side: str, as_of, last: dict, stop: float,
           params: dict, trend_side: str, regime: str):
    checked_side(side)
    rr = param(params, "target_rr", low=0.01)
    min_rr = param(params, "min_rr", low=0.01)
    if rr < min_rr or last["closed"] != as_utc(as_of):
        return []
    entry = last["close"]
    risk = entry - stop if side == "BUY" else stop - entry
    if risk <= 0 or not math.isfinite(risk):
        return []
    target = entry + risk * rr if side == "BUY" else entry - risk * rr
    if target <= 0:
        return []
    return [Signal(setup, side, as_utc(as_of), entry, stop, target,
                   last["closed"], trend_side, regime)]
