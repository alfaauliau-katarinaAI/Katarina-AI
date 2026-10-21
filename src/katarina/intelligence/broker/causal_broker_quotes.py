"""Causal MT5 quote reader for the existing single read-only observer.

MT5 symbol_info_tick may carry a server-local +integer-hour offset
and a further seconds-level lead. Historical copy_ticks_range returns
UTC-epoch milliseconds on this broker. Never treat the latest server
tick as a quote observed in the future of the VPS's decision clock.

The functions require UTC timezone-aware boundaries, verify actual
tick timestamps and bid/ask, and NEVER send/check a broker order.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite

MAX_TICKS_PER_QUERY=25000


from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerEventClock:
    """Two separate clocks; MT5 tick is the ONLY market decision time."""
    market_utc:datetime
    observed_vps_utc:datetime
    quote_age_seconds:float
    source:str="MT5_HISTORICAL_TICK_TIME_MSC_UTC"


def market_event_clock(tick_epoch,observed_vps_utc,*,max_age_seconds=90):
    """Use the actual last historical broker tick as event clock.

    VPS UTC is only a causal upper bound, not the candle/signal timestamp.
    No conversion to or from the broker's display timezone is allowed.
    """
    observed=aware_utc(observed_vps_utc)
    if (not isinstance(tick_epoch,(int,float)) or
        not isfinite(tick_epoch) or tick_epoch<=0 or
        not 0<max_age_seconds<=180):
        raise ValueError("invalid_market_clock_inputs")
    age=observed.timestamp()-float(tick_epoch)
    if age<0:
        raise ValueError("broker_tick_from_future")
    if age>max_age_seconds:
        raise ValueError("stale_market_tick")
    return BrokerEventClock(
        market_utc=datetime.fromtimestamp(float(tick_epoch),timezone.utc),
        observed_vps_utc=observed,
        quote_age_seconds=age,
    )


def closed_bars_as_of_market_tick(rows,market_utc,*,minimum=55):
    """Exclude all candles newer than MT5 event time, never VPS time.

    A candle ending AFTER the current broker tick must not enter analysis
    even if the VPS clock has already advanced to the next minute.
    """
    cutoff=aware_utc(market_utc)
    out=[]
    previous=None
    for bar in rows:
        end=aware_utc(bar.closed_at_utc)
        if previous is not None and end<=previous:
            raise ValueError("broker_bars_not_monotonic")
        previous=end
        if end<=cutoff:
            out.append(bar)
    if len(out)<minimum:
        raise ValueError("insufficient_completed_bars_as_of_mt5_tick")
    return out



def aware_utc(timestamp):
    if not isinstance(timestamp,datetime) or timestamp.tzinfo is None:
        raise ValueError("quote_clock_must_have_timezone")
    return timestamp.astimezone(timezone.utc)


def _fetch_ticks(mt5,symbol,start,end):
    if not symbol or end<=start:
        return ()
    a=mt5.copy_ticks_range(symbol,start,end,mt5.COPY_TICKS_INFO)
    if a is None or len(a)>MAX_TICKS_PER_QUERY:
        return ()
    return a


def _verified_quote(row,lower,upper):
    try:
        ts=float(row["time_msc"])/1000.0
        bid=float(row["bid"]);ask=float(row["ask"])
    except (KeyError,TypeError,ValueError,IndexError):
        return None
    if (not all(isfinite(v) for v in (ts,bid,ask)) or
        bid<=0 or ask<bid or ts<lower or ts>upper):
        return None
    return (bid,ask,ts)


def last_past_quote(mt5,symbol,as_of_utc,lookback_seconds=90):
    """Freshest real BID/ASK price quote with timestamp <= observed clock.

    Do not extrapolate data from a tick in the broker's future;
    no interpolation, normalization by guessing a fractional offset,
    or acceptance of a quote older than the bounded lookback.
    """
    now=aware_utc(as_of_utc)
    if not 0<lookback_seconds<=180:
        raise ValueError("invalid_quote_lookback")
    before=now-timedelta(seconds=lookback_seconds)
    arr=_fetch_ticks(mt5,symbol,before,now)
    upper=now.timestamp();lower=before.timestamp()
    # A stable maximum, rather than assuming broker arrays are sorted.
    matched=[q for q in (_verified_quote(row,lower,upper) for row in arr)
             if q is not None]
    if not matched:
        # An empty/oversized broad response gets three smaller same-broker queries.
        # Keep the original causal and age bounds; never substitute another feed.
        for seconds in (0,30,60):
            end=now-timedelta(seconds=seconds)
            start=max(before,end-timedelta(seconds=30))
            part=_fetch_ticks(mt5,symbol,start,end)
            matched=[q for q in (_verified_quote(row,lower,upper) for row in part) if q is not None]
            if matched:break
    return max(matched,key=lambda q:q[2]) if matched else None


def due_window_quote(mt5,symbol,due_epoch,now_epoch,max_delay=120):
    """Earliest actual tick after a precommitted markout deadline.

    This may be queried later (next 5-min cycle) via broker history;
    mark as RETROSPECTIVELY RECONCILED, not a real-time paper fill.
    Broker history uses UTC timestamps, NOT current terminal offset.
    """
    due=float(due_epoch);now=float(now_epoch)
    if (not all(isfinite(x) for x in (due,now)) or
        not 0<max_delay<=180 or due>=now):
        return None
    end=min(now,due+max_delay)
    if end<=due:
        return None
    arr=_fetch_ticks(
        mt5,symbol,datetime.fromtimestamp(due,timezone.utc),
        datetime.fromtimestamp(end,timezone.utc),
    )
    matched=[q for q in (_verified_quote(row,due,end) for row in arr)
             if q is not None]
    return min(matched,key=lambda q:q[2]) if matched else None
