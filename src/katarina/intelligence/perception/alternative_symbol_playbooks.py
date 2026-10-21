"""Per-market, distinct, pre-registered alternative research hypotheses.

XAU reversal = range sweep rejection on completed M1 candle, stop beyond
the wick, structural target inside opposite prior M1 range.
US30 reversal = failed breakout of 09:30-10:00 NY local range, return
into range; structural stop beyond rejection wick, target OR midpoint/edge.
JPN225 momentum = 09:30-11:30 JST breakout of 09:00-09:30 range aligned
with previous closed M5 EMA slope; stop behind boundary.
No NAS100 model is reused. This module is *research alternatives only*.
"""
from __future__ import annotations
from statistics import mean
from katarina.intelligence.perception.symbol_playbooks import (
    _bull,_bear,_ny_open_utc_minutes,_session)

SYMBOLS={
 "XAUUSD.vx":"gold_sweep_rejection_30m_structural_v2",
 "US30.vx":"dow_newyork_failed_break_mean_revert_v2",
 "JPN225.vx":"nikkei_tokyo_open_range_impulse_v2",
}
CAPS={"XAUUSD.vx":.35,"US30.vx":.35,"JPN225.vx":.40}
# _make in v1 maps family to original; alternative hypothesis needs
# independent family identity, and must refuse invalid geometry.
def _candidate(symbol,side,entry,stop,target,hold,atr,reason):
    if atr<=0:return []
    risk=entry-stop if side=="BUY" else stop-entry
    reward=target-entry if side=="BUY" else entry-target
    if risk<.30*atr or risk>4*atr or reward<1.10*risk:
        return []
    return [dict(symbol=symbol,family=SYMBOLS[symbol],side=side,
        hypothetical_stop=stop,hypothetical_target=target,
        signal_atr=atr,max_holding_minutes=hold,
        reference_structure=reason,research_only=True,
        live_authorized=False)]

def propose(symbol,m1,m5,day,now):
    if symbol not in SYMBOLS:raise ValueError("no_cross_market_alternative")
    if len(m1)<120 or len(m5)<120:return []
    if m1[-1]["time"]+60>now.timestamp() or m5[-1]["time"]+300>now.timestamp() or any(b["time"]+60>now.timestamp() for b in day):
        raise ValueError("unclosed_market_data_forbidden")
    tr=[max(a["high"]-a["low"],abs(a["high"]-p["close"]),
            abs(a["low"]-p["close"])) for p,a in zip(m1[-16:-1],m1[-15:])]
    atr=mean(tr[-14:])
    if atr<=0:return []
    c=m1[-1]
    if symbol=="XAUUSD.vx":
        # Liquidity sweep re-enters the 20-bar range on the *signal*
        # candle; wick evidence sufficient, not an inferred future swing.
        prev=m1[-21:-1]
        low=min(b["low"] for b in prev)
        high=max(b["high"] for b in prev)
        if c["low"]<low-.10*atr and c["close"]>low+.05*atr and (
             _bull(c,.35) or c["close"]>c["low"]+.70*(c["high"]-c["low"])):
            target=low+.75*(high-low)
            return _candidate(symbol,"BUY",c["close"],
                c["low"]-.15*atr,target,40,atr,"20_M1_lower_liquidity_sweep_rejection")
        if c["high"]>high+.10*atr and c["close"]<high-.05*atr and (
             _bear(c,.35) or c["close"]<c["high"]-.70*(c["high"]-c["low"])):
            target=high-.75*(high-low)
            return _candidate(symbol,"SELL",c["close"],
                c["high"]+.15*atr,target,40,atr,"20_M1_upper_liquidity_sweep_rejection")
        return []
    if symbol=="US30.vx":
        minute=now.hour*60+now.minute
        ten=_ny_open_utc_minutes(now,10)
        if not ten<=minute<=ten+150:return []
        orng=_session(day,_ny_open_utc_minutes(now,9,30)*60,ten*60)
        if len(orng)<25:return []
        hi=max(b["high"] for b in orng)
        lo=min(b["low"] for b in orng)
        mid=(hi+lo)/2
        if c["high"]>hi+.10*atr and c["close"]<hi-.1*atr and _bear(c,.35):
            return _candidate(symbol,"SELL",c["close"],
                    c["high"]+.10*atr,mid,55,atr,"NY_opening_range_failed_up_break")
        if c["low"]<lo-.10*atr and c["close"]>lo+.10*atr and _bull(c,.35):
            return _candidate(symbol,"BUY",c["close"],
                    c["low"]-.10*atr,mid,55,atr,"NY_opening_range_failed_down_break")
        return []
    if symbol=="JPN225.vx":
        # JPN225.vx broker's *observed* first UTC M1 quotes are around
        # 01:01, not the Tokyo cash exchange's theoretical 00:00 UTC.
        # Use the first historical M1 quote of the *current* UTC day,
        # only after it has genuinely appeared. No assumed candles.
        if not day:return []
        opened=int(day[0]["time"])%86400
        if not 45*60<=opened<=120*60:return []
        minute=now.hour*60+now.minute
        if not opened+35*60<=minute*60<=opened+180*60:return []
        opening=_session(day,opened,opened+30*60)
        if len(opening)<20:return []
        hi=max(b["high"] for b in opening)
        lo=min(b["low"] for b in opening)
        prev=m1[-2]
        if prev["close"]<=hi and c["close"]>hi+.10*atr and _bull(c,.55):
            stop=hi-.65*atr
            return _candidate(symbol,"BUY",c["close"],stop,
                    c["close"]+1.5*(c["close"]-stop),55,atr,
                    "Broker_first_30m_range_breakup_not_cash_open")
        if prev["close"]>=lo and c["close"]<lo-.10*atr and _bear(c,.55):
            stop=lo+.65*atr
            return _candidate(symbol,"SELL",c["close"],stop,
                    c["close"]-1.5*(stop-c["close"]),55,atr,
                    "Broker_first_30m_range_breakdown_not_cash_open")
    return []
