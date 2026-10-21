"""Frozen, closed-bar GOLD intraday shadow hypotheses.

Important: the forward research version below is independently identifiable
and is NOT claimed identical to the historically optimized EA/backtest.
It MUST earn fresh paper evidence. No model training, order routing or future
bars here. Signals outside the chosen UTC window are WAIT.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from math import isfinite

from katarina.adapters.mt5_shadow_read_only import ClosedBar, ShadowMarketSnapshot


@dataclass(frozen=True, slots=True)
class ShadowSetup:
    strategy_id: str
    side: str
    reason: str
    sl_distance: float
    rr: float
    hold_minutes: int


def _true_range(bar: ClosedBar, previous_close: float) -> float:
    return max(bar.high-bar.low, abs(bar.high-previous_close),
               abs(bar.low-previous_close))


def _atr14(rows: tuple[ClosedBar, ...]) -> float:
    if len(rows) < 16:
        raise ValueError("insufficient_atr_candles")
    tr=[_true_range(rows[i],rows[i-1].close) for i in range(1,len(rows))]
    # Wilder ATR14, warm-start with the first 14 true ranges.
    atr=sum(tr[:14])/14
    for v in tr[14:]:
        atr=(13*atr+v)/14
    if not isfinite(atr) or atr<=0:
        raise ValueError("invalid_atr")
    return atr


def _adx14(rows: tuple[ClosedBar, ...]) -> float:
    if len(rows) < 30:
        raise ValueError("insufficient_adx_candles")
    tr=[];plus=[];minus=[]
    for i in range(1,len(rows)):
        a,b=rows[i-1],rows[i]
        up=b.high-a.high;down=a.low-b.low
        tr.append(_true_range(b,a.close))
        plus.append(up if up>down and up>0 else 0.)
        minus.append(down if down>up and down>0 else 0.)
    period=14
    smooth_tr=sum(tr[:period])
    smooth_plus=sum(plus[:period])
    smooth_minus=sum(minus[:period])
    dx=[]
    for i in range(period,len(tr)):
        if i>period:
            smooth_tr=smooth_tr-smooth_tr/period+tr[i]
            smooth_plus=smooth_plus-smooth_plus/period+plus[i]
            smooth_minus=smooth_minus-smooth_minus/period+minus[i]
        plus_di=100*smooth_plus/smooth_tr if smooth_tr>0 else 0.
        minus_di=100*smooth_minus/smooth_tr if smooth_tr>0 else 0.
        total=plus_di+minus_di
        dx.append(100*abs(plus_di-minus_di)/total if total else 0.)
    if len(dx)<14:
        raise ValueError("insufficient_adx_warmup")
    adx=sum(dx[:14])/14
    for value in dx[14:]:
        adx=(13*adx+value)/14
    return adx


def _direction(rows: tuple[ClosedBar, ...], lookback: int) -> int:
    if len(rows)<lookback+1:
        return 0
    current=rows[-1].close;past=rows[-lookback-1].close
    return 1 if current>past else -1 if current<past else 0


def _efficiency(rows: tuple[ClosedBar, ...], lookback: int) -> float:
    sample=rows[-lookback-1:]
    if len(sample)!=lookback+1:
        return 0.
    travel=sum(abs(b.close-a.close) for a,b in zip(sample,sample[1:]))
    return abs(sample[-1].close-sample[0].close)/travel if travel>0 else 0.


class GoldShadowIntraday:
    STRATEGIES=("GOLD_OR_ADX20_SHADOW_V1","GOLD_VWAP_ADX25_SHADOW_V1")

    def analyze(self, snapshot: ShadowMarketSnapshot) -> tuple[ShadowSetup, ...]:
        if not snapshot.symbol.startswith("XAUUSD"):
            return tuple(ShadowSetup(k,"WAIT","symbol_not_gold",0.,0.,0)
                         for k in self.STRATEGIES)
        m5,h1,h4=snapshot.m5,snapshot.h1,snapshot.h4
        latest=m5[-1]
        if (latest.closed_at_utc>snapshot.observed_at_utc or
                h1[-1].closed_at_utc>snapshot.observed_at_utc or
                h4[-1].closed_at_utc>snapshot.observed_at_utc):
            raise ValueError("future_candle_in_research")
        if len(m5)<90 or len(h1)<40 or len(h4)<12:
            return tuple(ShadowSetup(k,"WAIT","insufficient_closed_bars",0.,0.,0)
                         for k in self.STRATEGIES)
        # 06:00-07:00 UTC is the CLOSED opening range; inspect signals
        # at 07:00-09:00 UTC, i.e. only after the full opening range exists.
        after=latest.closed_at_utc
        minute=after.hour*60+after.minute
        if minute < 420 or minute >= 540:
            return tuple(ShadowSetup(k,"WAIT","outside_07_09_utc_window",0.,0.,0)
                         for k in self.STRATEGIES)
        day=after.date()
        opening=[b for b in m5 if b.open_at_utc.date()==day
                 and 360 <= b.open_at_utc.hour*60+b.open_at_utc.minute < 420]
        if len(opening)!=12 or any(
                opening[i].open_at_utc-opening[i-1].open_at_utc !=
                timedelta(minutes=5)
                for i in range(1,12)):
            return tuple(ShadowSetup(k,"WAIT","opening_range_not_complete",0.,0.,0)
                         for k in self.STRATEGIES)
        atr=_atr14(h1)
        adx=_adx14(h1)
        high=max(x.high for x in opening);low=min(x.low for x in opening)
        side="WAIT";reason="no_aligned_opening_break"
        d1,d4=_direction(h1,5),_direction(h4,4)
        if d1==d4 and d1 and _efficiency(h4,8)>=.22 and adx>=20:
            if d1==1 and latest.close>high+.03*atr:
                side="BUY";reason="closed_m5_or_break_adx_h1h4"
            if d1==-1 and latest.close<low-.03*atr:
                side="SELL";reason="closed_m5_or_break_adx_h1h4"
        orb=ShadowSetup(self.STRATEGIES[0],side,reason,
                        .55*atr if side!="WAIT" else 0.,
                        2. if side!="WAIT" else 0.,
                        360 if side!="WAIT" else 0)

        weighted=m5[-73:-1]
        if len(weighted)!=72 or sum(max(0,b.tick_volume) for b in weighted)<=0:
            return (orb,ShadowSetup(self.STRATEGIES[1],"WAIT",
                                   "vwap_history_missing",0.,0.,0))
        denom=sum(max(0,b.tick_volume) for b in weighted)
        vwap=sum(((b.high+b.low+b.close)/3)*max(0,b.tick_volume)
                 for b in weighted)/denom
        prev=m5[-2]
        vwside="WAIT";vwreason="no_vwap_reclaim"
        if adx>=25:
            if prev.close<vwap-.1*atr and latest.close>vwap and latest.close>latest.open:
                vwside="BUY";vwreason="closed_m5_vwap_reclaim_adx25"
            if prev.close>vwap+.1*atr and latest.close<vwap and latest.close<latest.open:
                vwside="SELL";vwreason="closed_m5_vwap_reject_adx25"
        vwapsetup=ShadowSetup(self.STRATEGIES[1],vwside,vwreason,
                             .55*atr if vwside!="WAIT" else 0.,
                             1.5 if vwside!="WAIT" else 0.,
                             180 if vwside!="WAIT" else 0)
        return orb,vwapsetup
