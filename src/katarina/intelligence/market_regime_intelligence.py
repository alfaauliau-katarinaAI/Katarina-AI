"""KATARINA Market Regime Intelligence v1: closed-candle, symbol-specific.

This module classifies *observable evidence*, not probabilities of profit.
High timeframe (H1/M15) structure, M5 confirmation, optional M1 timing.
States: CONTINUATION_UP/DOWN, REVERSAL_UP/DOWN, SIDEWAYS,
TRANSITION, UNKNOWN. No order routing and no model promotion.
"""
from __future__ import annotations

from datetime import timezone
from math import isfinite
from statistics import mean
from katarina.intelligence.multi_market_brain import features
from katarina.intelligence.technical_regime import classify_market_regime

FRAME_SECONDS={"M1":60,"M5":300,"M15":900,"H1":3600}
# Fixed initial research hypotheses; never tune on the same archives
# and call the result independently validated.
PROFILES={
    "XAUUSD.vx":dict(trend_adx=23,range_adx=17,range_efficiency=.23,
                      reversal_sweep_atr=.10,minimum_mss_atr=.06),
    "NAS100.vx":dict(trend_adx=25,range_adx=18,range_efficiency=.22,
                      reversal_sweep_atr=.12,minimum_mss_atr=.07),
    "US30.vx":dict(trend_adx=24,range_adx=18,range_efficiency=.22,
                      reversal_sweep_atr=.12,minimum_mss_atr=.07),
    "JPN225.vx":dict(trend_adx=23,range_adx=18,range_efficiency=.24,
                      reversal_sweep_atr=.12,minimum_mss_atr=.07),
    "EURUSD.vx":dict(trend_adx=23,range_adx=17,range_efficiency=.23,
                      reversal_sweep_atr=.08,minimum_mss_atr=.05),
    "GBPUSD.vx":dict(trend_adx=24,range_adx=17,range_efficiency=.23,
                      reversal_sweep_atr=.10,minimum_mss_atr=.06),
    "USDJPY.vx":dict(trend_adx=24,range_adx=17,range_efficiency=.22,
                      reversal_sweep_atr=.09,minimum_mss_atr=.05),
}
STATES=("CONTINUATION_UP","CONTINUATION_DOWN",
        "LOCAL_CONTINUATION_UP","LOCAL_CONTINUATION_DOWN",
        "PULLBACK_UP","PULLBACK_DOWN",
        "REVERSAL_UP","REVERSAL_DOWN","SIDEWAYS","TRANSITION","UNKNOWN")
UTC=timezone.utc

def _unknown(reason):
    return dict(regime="UNKNOWN",direction="NONE",
        evidence_score_0_100=None,evidence_is_profit_probability=False,
        evidence_is_calibrated=False,reversal_confirmation=False,
        entry_authorized=False,model_promotion_allowed=False,
        observed_utc=None,reason_codes=[reason],frames={},
        symbol_profile_used=None,entry_timing="UNAVAILABLE")

def _validated_frame(raw,period,now,required=120):
    if raw is None or len(raw)<required:
        raise ValueError("insufficient_"+period+"_bars")
    bars=raw[-required:]
    seconds=FRAME_SECONDS[period]
    previous=None
    for i,b in enumerate(bars):
        t=float(b["time"])
        if not isfinite(t) or (previous is not None and t<=previous):
            raise ValueError("unordered_"+period+"_bars")
        previous=t
        if t+seconds>now.timestamp()+.01:
            raise ValueError("unfinished_"+period+"_bar")
        values=[float(b[k]) for k in ("open","high","low","close","tick_volume")]
        if not all(isfinite(v) and v>0 for v in values[:4]):
            raise ValueError("invalid_"+period+"_OHLC")
        if not isfinite(values[4]) or values[4]<0:
            raise ValueError("invalid_"+period+"_volume")
        if values[1]<max(values[0],values[3],values[2]) or values[2]>min(values[0],values[3]):
            raise ValueError("invalid_"+period+"_OHLC")
    # Only recent bar continuity is required: weekends and exchange
    # closures may occur earlier in the 120-bar indicator warmup.
    tail=bars[-4:]
    if any(float(b["time"])-float(a["time"])>seconds*2 for a,b in zip(tail,tail[1:])):
        raise ValueError("recent_"+period+"_gap")
    age=now.timestamp()-float(bars[-1]["time"])-seconds
    if not 0<=age<=2*seconds:
        raise ValueError("stale_"+period+"_bars")
    data=features(bars,seconds,now)
    data.pop("returns",None)
    return bars,data

def _range(f,profile):
    return (f["adx14"]<=profile["range_adx"] and
            f["efficiency"]<=profile["range_efficiency"])

def _trend(f,profile):
    if f["adx14"]<profile["trend_adx"] or f["efficiency"]<.27:
        return "NONE"
    if f["direction"]=="UP" and f["plus_di14"]>f["minus_di14"]:
        return "UP"
    if f["direction"]=="DOWN" and f["minus_di14"]>f["plus_di14"]:
        return "DOWN"
    return "NONE"

def _reversal_structure(bars,atr,profile):
    """Confirmed sweep -> break of *previous* structure on closed M5 bars.

    A sweep must precede a later closed displacement candle. This is
    a recent confirmed event, not a prediction of a future swing.
    """
    result=[]
    for j in range(len(bars)-7,len(bars)-1):
        past=bars[j-12:j]
        if len(past)<12:continue
        sweep=bars[j]
        upper=max(float(x["high"]) for x in past)
        lower=min(float(x["low"]) for x in past)
        previous_structure_upper=max(float(x["high"]) for x in past[-8:])
        previous_structure_lower=min(float(x["low"]) for x in past[-8:])
        for k in range(j+1,len(bars)):
            current=bars[k]
            body=abs(float(current["close"])-float(current["open"]))
            span=float(current["high"])-float(current["low"])
            if span<=0 or body/span<.55 or span<.8*atr:continue
            if (float(sweep["low"])<lower-profile["reversal_sweep_atr"]*atr
                  and float(current["close"])>
                    previous_structure_upper+profile["minimum_mss_atr"]*atr
                  and float(current["close"])>float(current["open"])):
                result.append(("UP",j,k))
            if (float(sweep["high"])>upper+profile["reversal_sweep_atr"]*atr
                  and float(current["close"])<
                    previous_structure_lower-profile["minimum_mss_atr"]*atr
                  and float(current["close"])<float(current["open"])):
                result.append(("DOWN",j,k))
    return result[-1] if result else None

def classify_regime(symbol, m5_closed, m15_closed, h1_closed, now, m1_closed=None):
    """Return causal, audited research classification without trade authority."""
    if symbol not in PROFILES:
        return _unknown("symbol_profile_not_registered")
    if now.tzinfo is None:
        return _unknown("missing_UTC_timezone")
    now=now.astimezone(UTC)
    profile=PROFILES[symbol]
    try:
        bars5,five=_validated_frame(m5_closed,"M5",now)
        bars15,fifteen=_validated_frame(m15_closed,"M15",now)
        bars1h,hour=_validated_frame(h1_closed,"H1",now)
        minute=None
        if m1_closed is not None:
            bars1,minute=_validated_frame(m1_closed,"M1",now,required=60)
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        return _unknown(str(exc))
    htrend=_trend(hour,profile)
    mtrend=_trend(fifteen,profile)
    ftrend=_trend(five,profile)
    reason=[]
    regime="TRANSITION"
    reversal=_reversal_structure(bars5,five["atr"],profile)
    reversed_bias=(reversal and (
         (reversal[0]=="UP" and htrend=="DOWN") or
         (reversal[0]=="DOWN" and htrend=="UP")))
    # Require confirmed post-sweep displacement PLUS M15 no longer
    # strictly trending against the new side. A sweep by itself
    # cannot be labeled a market reversal.
    if reversed_bias and mtrend not in ("DOWN" if reversal[0]=="UP" else "UP",):
        if (reversal[0]=="UP" and five["direction"]=="UP" and
            fifteen["close_age_seconds"]>=0 and
            float(bars15[-1]["close"])>fifteen["ema20"]):
            regime="REVERSAL_UP"
        elif (reversal[0]=="DOWN" and five["direction"]=="DOWN" and
              float(bars15[-1]["close"])<fifteen["ema20"]):
            regime="REVERSAL_DOWN"
        if regime.startswith("REVERSAL"):
            reason.append("sweep_then_closed_M5_structure_break")
            reason.append("opposite_prior_H1_context")
    if regime=="TRANSITION":
        # Distinguish dominant H1/M15 direction from a tactical M5
        # pullback. Do not require all three to be STRONG ADX trends:
        # ADX strength and EMA orientation measure different qualities.
        bias_up=(hour["direction"]=="UP" and fifteen["direction"]=="UP"
                 and hour["adx14"]>=profile["range_adx"]
                 and fifteen["adx14"]>=profile["range_adx"]+1
                 and hour["efficiency"]>=.12)
        bias_down=(hour["direction"]=="DOWN" and fifteen["direction"]=="DOWN"
                 and hour["adx14"]>=profile["range_adx"]
                 and fifteen["adx14"]>=profile["range_adx"]+1
                 and hour["efficiency"]>=.12)
        if bias_up and five["direction"]=="UP" and five["adx14"]>=16:
            regime="CONTINUATION_UP"
            reason.append("H1_M15_up_bias_and_M5_up_confirmation")
        elif bias_down and five["direction"]=="DOWN" and five["adx14"]>=16:
            regime="CONTINUATION_DOWN"
            reason.append("H1_M15_down_bias_and_M5_down_confirmation")
        elif bias_up and five["direction"]=="DOWN":
            regime="PULLBACK_UP"
            reason.append("H1_M15_up_bias_but_M5_countertrend")
        elif bias_down and five["direction"]=="UP":
            regime="PULLBACK_DOWN"
            reason.append("H1_M15_down_bias_but_M5_countertrend")
        elif (_range(fifteen,profile) and _range(five,profile)):
            regime="SIDEWAYS"
            reason.append("M15_M5_low_ADX_low_directional_efficiency")
        elif ((hour["direction"]=="MIXED" or _range(hour,profile))
              and fifteen["direction"]==five["direction"]
              and fifteen["direction"] in ("UP","DOWN")
              and fifteen["adx14"]>=profile["trend_adx"]
              and five["adx14"]>=profile["range_adx"]):
            regime="LOCAL_CONTINUATION_"+fifteen["direction"]
            reason.append("M15_M5_local_trend_with_H1_neutral")
        else:
            reason.append("timeframe_conflict_or_unconfirmed_reversal")
    if reversal and not regime.startswith("REVERSAL"):
        reason.append("structure_event_observed_but_not_confirmed_reversal")
    strengths=(hour["adx14"],fifteen["adx14"],five["adx14"])
    if regime.startswith("CONTINUATION") or regime.startswith("LOCAL_CONTINUATION"):
        score=round(min(95,max(50,50+(mean(strengths)-
             profile["trend_adx"])*.75+10*min(1,hour["efficiency"]))),1)
        direction="UP" if regime.endswith("_UP") else "DOWN"
    elif regime.startswith("PULLBACK"):
        score=round(min(85,max(50,55+fifteen["adx14"]*.35)),1)
        direction="UP" if regime.endswith("_UP") else "DOWN"
    elif regime.startswith("REVERSAL"):
        score=round(min(85,max(50,55+five["adx14"]*.3+
                                five["efficiency"]*8)),1)
        direction="UP" if regime.endswith("_UP") else "DOWN"
    elif regime=="SIDEWAYS":
        score=round(min(90,max(50,65-(mean(strengths)-
                                         profile["range_adx"])*.6)),1)
        direction="NONE"
    else:
        score=None
        direction="NONE"
    timing="UNAVAILABLE"
    if minute is not None:
        if direction in ("UP","DOWN"):
            timing="M1_ALIGNED" if minute["direction"]==direction else "M1_NOT_ALIGNED"
        else:
            timing="NO_DIRECTIONAL_ENTRY"
    snapshots={}
    for label,frame in (("H1",hour),("M15",fifteen),("M5",five)):
        snapshots[label]=dict(
            direction=frame["direction"],adx14=round(frame["adx14"],3),
            plus_di14=round(frame["plus_di14"],3),
            minus_di14=round(frame["minus_di14"],3),
            efficiency=round(frame["efficiency"],4),
            atr=frame["atr"],close_age_seconds=frame["close_age_seconds"],
            technical_regime_baseline=classify_market_regime(frame))
    return dict(regime=regime,direction=direction,
       evidence_score_0_100=score,evidence_is_profit_probability=False,
       evidence_is_calibrated=False,
       reversal_confirmation=regime.startswith("REVERSAL"),
       entry_authorized=False,model_promotion_allowed=False,
       observed_utc=now.isoformat(),reason_codes=reason,
       frames=snapshots,symbol_profile_used=symbol,
       entry_timing=timing,regime_engine_version="market_regime_v1")
