"""Causal playbook semantics for KATARINA's explainable research Brain.

A playbook name should describe an observable event, not merely a candle
color. This module rejects false 'pullbacks', untested 'breakout retests',
range fades without real edge rejection, and reversals without sweeps.

Pure, no broker API. RESEARCH ONLY. This does not estimate profitability.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Sequence

@dataclass(frozen=True)
class SemanticSetup:
    side: str
    playbook: str
    pattern_confirmed: bool
    evidence: tuple[str,...]
    blockers: tuple[str,...]
    setup_level: float | None
    next_trigger: str
    research_only: bool = True
    live_execution_authorized: bool = False

def tr(b,a):
    return max(b.high-b.low,abs(b.high-a.close),abs(b.low-a.close))

class CausalSetupValidator:
    def __init__(self,max_spread_atr=.35):
        if not 0<max_spread_atr<1:raise ValueError("bad_spread_limit")
        self.max_spread_atr=max_spread_atr

    def assess(self, *,side:str,playbook:str,m5:Sequence,
               m15:Sequence,h1:Sequence,spread:float,as_of_utc:datetime)->SemanticSetup:
        if side not in ("BUY","SELL") or as_of_utc.tzinfo is None:
            raise ValueError("invalid_side_or_timestamp")
        if any(len(x)<40 for x in (m5,m15,h1)):
            raise ValueError("insufficient_candles")
        if not isfinite(spread) or spread<0:raise ValueError("invalid_spread")
        for candles in (m5,m15,h1):
            prev=None
            for b in candles:
                if (b.closed_at_utc.tzinfo is None or b.closed_at_utc>as_of_utc
                    or (prev is not None and b.closed_at_utc<=prev)):
                    raise ValueError("future_or_unordered_candle")
                prev=b.closed_at_utc
                if not all(isfinite(x) and x>0 for x in (b.open,b.high,b.low,b.close)):
                    raise ValueError("invalid_price")
                if b.high<max(b.open,b.close) or b.low>min(b.open,b.close):
                    raise ValueError("invalid_bar_geometry")
        direction=1 if side=="BUY" else -1
        atr=sum(tr(b,a) for a,b in zip(m5[-15:-1],m5[-14:]))/14
        if atr<=0:raise ValueError("nonpositive_atr")
        current=m5[-1];previous=m5[-2]
        blockers=[];positive=[]
        def ok(label,condition):
            if condition:positive.append(label)
            else:blockers.append(label)
        if spread/atr>self.max_spread_atr:
            blockers.append("spread_exceeds_semantic_setup_budget")
        directional_close=direction*(current.close-current.open)>0
        candle_reaction=direction*(current.close-previous.close)>0
        body=abs(current.close-current.open)
        wick=(min(current.open,current.close)-current.low if direction>0
              else current.high-max(current.open,current.close))
        real_rejection=wick>=max(.2*atr,.8*body)
        before=m5[-22:-2] # EXCLUDE both prior breakout/retest bars
        top=max(x.high for x in before)
        bottom=min(x.low for x in before)
        setup_level=None
        if playbook=="TREND_PULLBACK":
            # Actual counter-direction CLOSED candles, not any bullish/bearish
            # color within a trend. This corrects legacy Trend Pullback rule.
            prior=m5[-9:-1]
            counter=sum(direction*(x.close-x.open)<0 for x in prior)
            prior_impulse=(
                max(x.high for x in m5[-26:-9]) if direction>0
                else min(x.low for x in m5[-26:-9])
            )
            corrective_extreme=(
                min(x.low for x in prior) if direction>0
                else max(x.high for x in prior)
            )
            actual_retrace=(
                corrective_extreme < prior_impulse-.22*atr if direction>0
                else corrective_extreme > prior_impulse+.22*atr
            )
            mtf15=direction*(m15[-1].close-m15[-10].close)
            mtf1=direction*(h1[-1].close-h1[-10].close)
            ok("prior_countertrend_closed_candles",counter>=2)
            ok("prior_correction_after_impulse",actual_retrace)
            ok("trend_multitimeframe_supported",mtf15>0 or mtf1>0)
            ok("closed_candle_resumption",directional_close and candle_reaction)
            ok("entry_not_far_from_retrace",abs(current.close-corrective_extreme)<=3*atr)
            setup_level=corrective_extreme
        elif playbook=="RANGE_FADE":
            level=bottom if direction>0 else top
            breach=(current.low<bottom if direction>0 else current.high>top)
            reclaim=(current.close>bottom+.04*atr if direction>0
                     else current.close<top-.04*atr)
            ok("prior_range_extreme_tested",breach)
            ok("close_back_inside_prior_range",reclaim)
            ok("rejection_wick_or_engulfing",real_rejection or
               (directional_close and body>=.6*atr))
            setup_level=level
        elif playbook=="BREAKOUT_RETEST":
            level=top if direction>0 else bottom
            prior_broke=(previous.close>top+.06*atr if direction>0
                         else previous.close<bottom-.06*atr)
            touched=(current.low<=level+.18*atr if direction>0
                     else current.high>=level-.18*atr)
            held=(current.close>level+.04*atr if direction>0
                  else current.close<level-.04*atr)
            ok("prior_closed_candle_broke_earlier_range",prior_broke)
            ok("new_candle_retested_breakout_level",touched)
            ok("retest_closed_in_breakout_direction",held and directional_close)
            setup_level=level
        elif playbook=="REVERSAL_RECLAIM":
            # Sweep and reclaim must refer to PREVIOUS channel.
            level=bottom if direction>0 else top
            swept=(current.low<bottom if direction>0 else current.high>top)
            reclaimed=(current.close>bottom+.05*atr if direction>0
                       else current.close<top-.05*atr)
            ok("prior_swing_liquidity_swept",swept)
            ok("swept_structure_reclaimed",reclaimed)
            ok("reversal_bar_rejection",real_rejection and directional_close)
            setup_level=level
        else:
            blockers.append("unsupported_playbook")
        next_trigger=("Candidate only; wait for independent validation, verified news and risk checks."
                      if not blockers else
                      "Wait for genuine price-action evidence: "+", ".join(blockers[:3]))
        return SemanticSetup(side,playbook,not blockers,tuple(positive),
            tuple(blockers),round(setup_level,9) if setup_level is not None else None,
            next_trigger)