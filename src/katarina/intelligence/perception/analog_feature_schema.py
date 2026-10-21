"""Stable causal market snapshot embedding shared by lab and observer.

This is not a trained prediction model and exposes no broker actions.
"""
from __future__ import annotations
from datetime import datetime
from math import sin,cos,pi,isfinite

CLAMP=.025
FRAME_LABELS=("M5","M15","H1")
FEATURE_SCHEMA="causal_mtf_14plus_regime7_v1"

def _signed(state):
    return 1. if state=="UP" else -1. if state=="DOWN" else 0.

def make_features(row,model):
    if model not in ("technical","technical_plus_regime","regime_only"):
        raise ValueError("unregistered_prediction_feature_family")
    feat=[]
    for timeframe in FRAME_LABELS:
        context=row["frames"][timeframe]
        feat.extend((
          _signed(context["direction"]),
          float(context["adx14"])/100.,
          (float(context["plus_di14"])-float(context["minus_di14"]))/100.,
          float(context["efficiency"])))
    clock=datetime.fromisoformat(row["close_time_utc"])
    if clock.tzinfo is None:
        raise ValueError("no_time_zone_on_features")
    h=(clock.timestamp()%86400)/86400*2*pi
    feat.extend((sin(h),cos(h)))
    if model in ("technical_plus_regime","regime_only"):
        state=row["regime"]
        groups=("CONTINUATION","LOCAL_CONTINUATION","PULLBACK",
                "REVERSAL","SIDEWAYS","TRANSITION")
        regime_feat=[float(state.startswith(k))
                     if k in ("CONTINUATION","LOCAL_CONTINUATION","PULLBACK","REVERSAL")
                     else float(state==k) for k in groups]
        regime_feat.append(1. if state.endswith("_UP") else -1. if state.endswith("_DOWN") else 0.)
        if model=="regime_only":feat=regime_feat
        else:feat+=regime_feat
    if not all(isfinite(v) for v in feat):
        raise ValueError("non_finite_prediction_embedding")
    return feat
