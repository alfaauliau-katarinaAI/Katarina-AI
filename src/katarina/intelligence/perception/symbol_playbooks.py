"""Disjoint market playbooks. Never fall back to another instrument's model.

All rules causal and research-only. Each broker symbol has its own:
event definition, session, structural stop, profit target, holding period.
No order API, no adaptive cross-symbol parameter sharing.
"""
from __future__ import annotations

from datetime import datetime,timezone
from math import isfinite
from statistics import mean
from katarina.intelligence.perception.screening import features

UTC=timezone.utc

def _nth_sunday(year,month,n):
    first=datetime(year,month,1,tzinfo=UTC)
    day=1+(6-first.weekday())%7+7*(n-1)
    return day

def _last_sunday(year,month):
    from calendar import monthrange
    last=monthrange(year,month)[1]
    dt=datetime(year,month,last,tzinfo=UTC)
    return last-(dt.weekday()+1)%7

def _ny_open_utc_minutes(now,local_hour,local_minute=0):
    # US DST: second Sunday March 07:00 UTC until first Sunday Nov
    # 06:00 UTC; no local timezone database dependency on Windows 2012.
    year=now.year
    start=datetime(year,3,_nth_sunday(year,3,2),7,tzinfo=UTC)
    stop=datetime(year,11,_nth_sunday(year,11,1),6,tzinfo=UTC)
    eastern_offset=4 if start<=now<stop else 5
    return (local_hour+eastern_offset)*60+local_minute

def _london_start_utc_hour(now):
    # UK DST: last Sunday March 01:00 UTC to last Sunday Oct 01:00 UTC.
    year=now.year
    start=datetime(year,3,_last_sunday(year,3),1,tzinfo=UTC)
    stop=datetime(year,10,_last_sunday(year,10),1,tzinfo=UTC)
    return 7 if start<=now<stop else 8

SYMBOLS={
 "XAUUSD.vx":"gold_sweep_shift_confirm_v1",
 "NAS100.vx":"nas_trend_pullback_continuation_v1",
 "US30.vx":"dow_ny_opening_range_break_v1",
 "JPN225.vx":"nikkei_tokyo_range_retest_v1",
 "EURUSD.vx":"eur_london_asian_range_break_v1",
 "GBPUSD.vx":"gbp_london_asian_sweep_fade_v1",
 "USDJPY.vx":"uj_tokyo_open_range_momentum_v1",
}
# Unrelated definitions intentionally have no default symbol.
CAPS={"XAUUSD.vx":.40,"NAS100.vx":.35,"US30.vx":.35,
      "JPN225.vx":.40,"EURUSD.vx":.32,"GBPUSD.vx":.32,
      "USDJPY.vx":.32}

def _ema(bars,n=20):
    v=float(bars[0]["close"]);w=2/(n+1)
    for r in bars[1:]:
        v+=w*(float(r["close"])-v)
    return v

def _bull(c,min_fraction=.45):
    rng=c["high"]-c["low"]
    return rng>0 and c["close"]>c["open"] and (
        c["close"]-c["open"])/rng>=min_fraction

def _bear(c,min_fraction=.45):
    rng=c["high"]-c["low"]
    return rng>0 and c["close"]<c["open"] and (
        c["open"]-c["close"])/rng>=min_fraction

def _make(symbol,side,entry_signal,stop,tp,minutes,source,atr):
    if not all(isfinite(v) for v in (entry_signal,stop,tp,atr)) or atr<=0:
        return []
    risk=abs(entry_signal-stop); reward=abs(tp-entry_signal)
    if risk<=0 or reward<=0:return []
    if side=="BUY" and not (stop<entry_signal<tp):return []
    if side=="SELL" and not (tp<entry_signal<stop):return []
    if risk<.30*atr or risk>4.0*atr or reward/risk<1.05 or reward/risk>4.0:
        return []
    return [dict(symbol=symbol,family=SYMBOLS[symbol],side=side,
        structural_entry_reference=entry_signal,
        hypothetical_stop=stop,hypothetical_target=tp,
        target_r_multiple=reward/risk,signal_atr=atr,
        max_holding_minutes=minutes,reference_structure=source,
        has_broker_filled_trade=False,live_authorized=False)]

def _session(day_bars,begin,end):
    return [b for b in day_bars if begin<=int(b["time"])%86400<end]

def _gold(m1,m5,day,now,atr):
    # Last fully closed candle confirms displacement after a prior sweep.
    prior=m1[-23:-3]
    if len(prior)<20:return []
    sweep=m1[-3]; impulse=m1[-2]; confirm=m1[-1]
    lower=min(b["low"] for b in prior)
    upper=max(b["high"] for b in prior)
    if impulse["tick_volume"]<1.20*mean(b["tick_volume"] for b in m1[-23:-3]):
        return []
    if impulse["high"]-impulse["low"]<.85*atr:return []
    if (sweep["low"]<lower-.05*atr and sweep["close"]>lower
       and _bull(impulse,.60) and impulse["close"]>sweep["high"]+.05*atr
       and confirm["low"]<impulse["close"] and _bull(confirm,.35)
       and confirm["close"]>impulse["open"]
       and m5[-1]["close"]>=_ema(m5,50)-.2*atr):
        stop=sweep["low"]-.12*atr
        target=max(b["high"] for b in m1[-75:-3])
        return _make("XAUUSD.vx","BUY",confirm["close"],stop,target,35,
                     "sweep_low_then_displacement_then_confirm",atr)
    if (sweep["high"]>upper+.05*atr and sweep["close"]<upper
       and _bear(impulse,.60) and impulse["close"]<sweep["low"]-.05*atr
       and confirm["high"]>impulse["close"] and _bear(confirm,.35)
       and confirm["close"]<impulse["open"]
       and m5[-1]["close"]<=_ema(m5,50)+.2*atr):
        stop=sweep["high"]+.12*atr
        target=min(b["low"] for b in m1[-75:-3])
        return _make("XAUUSD.vx","SELL",confirm["close"],stop,target,35,
                     "sweep_high_then_displacement_then_confirm",atr)
    return []

def _dow(m1,m5,day,now,atr):
    minute=now.hour*60+now.minute
    ten=_ny_open_utc_minutes(now,10)
    if not ten<=minute<=ten+150:return []
    opening=_session(day,_ny_open_utc_minutes(now,9,30)*60,ten*60)
    if len(opening)<25:return []
    hi=max(x["high"] for x in opening);lo=min(x["low"] for x in opening)
    if not 1.0*atr<hi-lo<12*atr:return []
    candle=m1[-1];previous=m1[-2]
    if previous["close"]<=hi and candle["close"]>hi+.10*atr and _bull(candle,.65):
        stop=hi-.85*atr
        target=candle["close"]+1.4*(candle["close"]-stop)
        return _make("US30.vx","BUY",candle["close"],stop,target,50,
                     "first_NY_opening_range_up_break",atr)
    if previous["close"]>=lo and candle["close"]<lo-.10*atr and _bear(candle,.65):
        stop=lo+.85*atr
        target=candle["close"]-1.4*(stop-candle["close"])
        return _make("US30.vx","SELL",candle["close"],stop,target,50,
                     "first_NY_opening_range_down_break",atr)
    return []

def _nas(m1,m5,day,now,atr):
    minute=now.hour*60+now.minute
    if not _ny_open_utc_minutes(now,9,40)<=minute<=_ny_open_utc_minutes(now,15):return []
    c=m1[-1];p=m1[-2]
    ctx=features(m5,300,now)
    if ctx["adx14"]<24 or ctx["efficiency"]<.25:return []
    ema_before=_ema(m1[:-1]);ema_now=_ema(m1)
    if (ctx["direction"]=="UP" and p["low"]<ema_before-.15*atr
        and c["close"]>ema_now+.1*atr and c["close"]>p["high"]
        and _bull(c,.55)):
        stop=min(x["low"] for x in m1[-6:])-.10*atr
        target=c["close"]+1.65*(c["close"]-stop)
        return _make("NAS100.vx","BUY",c["close"],stop,target,45,
                     "NY_trend_reclaim_after_M1_dip",atr)
    if (ctx["direction"]=="DOWN" and p["high"]>ema_before+.15*atr
        and c["close"]<ema_now-.1*atr and c["close"]<p["low"]
        and _bear(c,.55)):
        stop=max(x["high"] for x in m1[-6:])+.10*atr
        target=c["close"]-1.65*(stop-c["close"])
        return _make("NAS100.vx","SELL",c["close"],stop,target,45,
                     "NY_trend_reclaim_after_M1_rally",atr)
    return []

def _eur(m1,m5,day,now,atr):
    minute=now.hour*60+now.minute
    london=_london_start_utc_hour(now)
    if not london*60<=minute<(london+4)*60:return []
    asia=_session(day,0,london*3600)
    if len(asia)<180:return []
    hi=max(x["high"] for x in asia);lo=min(x["low"] for x in asia)
    c=m1[-1];p=m1[-2]
    if (p["close"]<=hi and c["close"]>hi+.12*atr
        and _bull(c,.65) and m5[-1]["close"]>_ema(m5,20)):
        stop=hi-.8*atr;target=c["close"]+1.3*(c["close"]-stop)
        return _make("EURUSD.vx","BUY",c["close"],stop,target,50,
                     "London_break_above_Asian_session_high",atr)
    if (p["close"]>=lo and c["close"]<lo-.12*atr
        and _bear(c,.65) and m5[-1]["close"]<_ema(m5,20)):
        stop=lo+.8*atr;target=c["close"]-1.3*(stop-c["close"])
        return _make("EURUSD.vx","SELL",c["close"],stop,target,50,
                     "London_break_below_Asian_session_low",atr)
    return []

def _gbp(m1,m5,day,now,atr):
    minute=now.hour*60+now.minute
    london=_london_start_utc_hour(now)
    if not london*60<=minute<=london*60+210:return []
    asia=_session(day,0,london*3600)
    if len(asia)<180:return []
    hi=max(b["high"] for b in asia);lo=min(b["low"] for b in asia)
    mid=(hi+lo)/2;c=m1[-1]
    if c["high"]>hi+.1*atr and c["close"]<hi-.05*atr and _bear(c,.50):
        stop=c["high"]+.12*atr
        return _make("GBPUSD.vx","SELL",c["close"],stop,mid,55,
                     "London_fakeout_above_Asia_then_midrange_revert",atr)
    if c["low"]<lo-.1*atr and c["close"]>lo+.05*atr and _bull(c,.50):
        stop=c["low"]-.12*atr
        return _make("GBPUSD.vx","BUY",c["close"],stop,mid,55,
                     "London_fakeout_below_Asia_then_midrange_revert",atr)
    return []

def _jpy(m1,m5,day,now,atr):
    minute=now.hour*60+now.minute
    if not 30<=minute<=3*60:return []
    opening=_session(day,0,30*60)
    if len(opening)<25:return []
    hi=max(b["high"] for b in opening);lo=min(b["low"] for b in opening)
    c=m1[-1];p=m1[-2]
    if m5[-1]["close"]>_ema(m5,50) and p["close"]<=hi and (
        c["close"]>hi+.08*atr) and _bull(c,.55):
        stop=hi-.75*atr
        target=c["close"]+1.5*(c["close"]-stop)
        return _make("USDJPY.vx","BUY",c["close"],stop,target,70,
                     "Tokyo_30min_range_momentum_up",atr)
    if m5[-1]["close"]<_ema(m5,50) and p["close"]>=lo and (
        c["close"]<lo-.08*atr) and _bear(c,.55):
        stop=lo+.75*atr
        target=c["close"]-1.5*(stop-c["close"])
        return _make("USDJPY.vx","SELL",c["close"],stop,target,70,
                     "Tokyo_30min_range_momentum_down",atr)
    return []

def _nikkei(m1,m5,day,now,atr):
    minute=now.hour*60+now.minute
    if not 35<=minute<=2*60+30:return []
    opening=_session(day,0,30*60)
    if len(opening)<25:return []
    hi=max(x["high"] for x in opening);lo=min(x["low"] for x in opening)
    c=m1[-1];p=m1[-2]
    if (p["close"]>hi+.08*atr and c["low"]<=hi+.1*atr and
         c["close"]>hi+.1*atr and _bull(c,.40)):
        stop=hi-.50*atr
        return _make("JPN225.vx","BUY",c["close"],stop,
                     c["close"]+1.25*(c["close"]-stop),50,
                     "Tokyo_open_break_then_level_retest_up",atr)
    if (p["close"]<lo-.08*atr and c["high"]>=lo-.1*atr and
         c["close"]<lo-.1*atr and _bear(c,.40)):
        stop=lo+.50*atr
        return _make("JPN225.vx","SELL",c["close"],stop,
                     c["close"]-1.25*(stop-c["close"]),50,
                     "Tokyo_open_break_then_level_retest_down",atr)
    return []

FUNCTIONS={"XAUUSD.vx":_gold,"NAS100.vx":_nas,"US30.vx":_dow,
   "JPN225.vx":_nikkei,"EURUSD.vx":_eur,"GBPUSD.vx":_gbp,
   "USDJPY.vx":_jpy}

def propose(symbol,m1_closed,m5_closed,day_closed,now):
    if symbol not in FUNCTIONS:
        raise ValueError("symbol_playbook_not_registered")
    if len(m1_closed)<120 or len(m5_closed)<120:
        return []
    if m1_closed[-1]["time"]+60>now.timestamp() or (
        m5_closed[-1]["time"]+300>now.timestamp()):
        raise ValueError("unfinished_candle_forbidden")
    if m5_closed[-1]["time"]+300 < now.timestamp()-600:
        return []
    bars=sorted(day_closed,key=lambda b:b["time"])
    if any(b["time"]+60>now.timestamp() for b in bars):
        raise ValueError("day_history_contains_future")
    tr=[max(cur["high"]-cur["low"],
             abs(cur["high"]-prev["close"]),abs(cur["low"]-prev["close"]))
        for prev,cur in zip(m1_closed[-16:-1],m1_closed[-15:])]
    atr=mean(tr[-14:])
    if atr<=0:return []
    return FUNCTIONS[symbol](m1_closed,m5_closed,bars,now,atr)
