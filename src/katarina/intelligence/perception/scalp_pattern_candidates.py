"""Frozen objective scalp pattern candidates from *closed* market bars.

Reference families: trend EMA reclaim, sweep-and-reclaim, breakout retest.
No live orders; historical exploration only; cannot infer future fills.
"""
from __future__ import annotations
from datetime import timezone
from math import isfinite
from statistics import mean

from katarina.intelligence.perception.screening import features
from katarina.intelligence.perception.technical_regime import classify_market_regime
from katarina.intelligence.shadow.shadow_hypotheses import propose

UTC=timezone.utc
FAMILIES=("ema20_trend_reclaim_v2","liquidity_sweep_reclaim_v2",
          "breakout_retest_v2","impulse_break_baseline_v1")

def entry_features(candles,now):
    ohlc=candles[-120:]
    result=features(ohlc,60,now)
    return result

def compact_ema(bars,length=20):
    alpha=2/(length+1)
    result=float(bars[0]["close"])
    for b in bars[1:]:
        result+=alpha*(float(b["close"])-result)
    return result

def propose_family(m1_bars,m5_bars,now):
    """Return fixed independent hypotheses; no hindsight or unfinished M5."""
    if len(m1_bars)<120 or len(m5_bars)<120:
        return []
    latest=m1_bars[-1]
    pre=m1_bars[-2]
    high,low,close,opening=(float(latest[k]) for k in
       ("high","low","close","open"))
    width=high-low
    if width<=0 or not low<=min(opening,close)<=max(opening,close)<=high:
        return []
    avg_volume=mean(float(b["tick_volume"]) for b in m1_bars[-21:-1])
    if avg_volume<=0:
        return []
    volume_ratio=float(latest["tick_volume"])/avg_volume
    body=abs(close-opening)/width
    up=close>opening and close>=low+.65*width
    down=close<opening and close<=high-.65*width
    if not (up or down):
        return []
    short=compact_ema(m1_bars[-120:])
    prev_ema=compact_ema(m1_bars[-121:-1]) if len(m1_bars)>=121 else compact_ema(m1_bars[-120:-1])
    # Signal candle may be current closed bar. Previous-bar EMA computed only
    # from previous CLOSED candles and does not peek at the signal close.
    ctx=features(m5_bars[-120:],300,now)
    if ctx["close_age_seconds"]>600 or not 0<=ctx["close_age_seconds"]:
        return []
    recent=entry_features(m1_bars,now)
    atr=recent["atr"]
    if not isfinite(atr) or atr<=0:return []
    trend_up=ctx["direction"]=="UP" and ctx["adx14"]>=18 and ctx["plus_di14"]>ctx["minus_di14"]
    trend_down=ctx["direction"]=="DOWN" and ctx["adx14"]>=18 and ctx["minus_di14"]>ctx["plus_di14"]
    output=[]
    # Signed continuation after the pullback touched/crossed the fast EMA.
    for side,ok in (("BUY",up and trend_up),("SELL",down and trend_down)):
        if not ok or body<.45 or volume_ratio<.9:continue
        condition=(float(pre["close"])<=prev_ema and close>short+.02*atr
                   if side=="BUY" else
                   float(pre["close"])>=prev_ema and close<short-.02*atr)
        if condition:
            output.append(dict(family=FAMILIES[0],side=side,atr=atr,
                               context_adx=ctx["adx14"],volume_ratio=volume_ratio))
    # Liquidity sweep and return, with directional M5 bias not strongly opposite.
    support=min(float(b["low"]) for b in m1_bars[-13:-1])
    resistance=max(float(b["high"]) for b in m1_bars[-13:-1])
    for side,ok in (("BUY",up and ctx["direction"]!="DOWN"),
                    ("SELL",down and ctx["direction"]!="UP")):
        if not ok or body<.3 or volume_ratio<.9:continue
        condition=(low<support-.05*atr and close>support+.08*atr
                   if side=="BUY" else
                   high>resistance+.05*atr and close<resistance-.08*atr)
        if condition:
            output.append(dict(family=FAMILIES[1],side=side,atr=atr,
                               context_adx=ctx["adx14"],volume_ratio=volume_ratio))
    # Prior candle broke a known 12-bar range. Current bar retests from
    # beyond it and confirms by closing on the same side, all bars closed.
    p_high=max(float(b["high"]) for b in m1_bars[-14:-2])
    p_low=min(float(b["low"]) for b in m1_bars[-14:-2])
    for side,ok in (("BUY",up and trend_up),("SELL",down and trend_down)):
        if not ok or body<.4 or volume_ratio<.85:continue
        condition=(float(pre["close"])>p_high+.08*atr and
                   low<=p_high+.12*atr and close>p_high+.12*atr
                   if side=="BUY" else
                   float(pre["close"])<p_low-.08*atr and
                   high>=p_low-.12*atr and close<p_low-.12*atr)
        if condition:
            output.append(dict(family=FAMILIES[2],side=side,atr=atr,
                               context_adx=ctx["adx14"],volume_ratio=volume_ratio))
    regime=classify_market_regime(ctx)
    existing=propose(dict(m1=recent,m5=ctx,m1_bars=m1_bars[-120:],
                 allowed_sides=["BUY","SELL"],regime_detail=regime))
    if existing:
        side=existing[0]["side"]
        output.append(dict(family=FAMILIES[3],side=side,atr=atr,
                           context_adx=ctx["adx14"],volume_ratio=volume_ratio))
    return output
