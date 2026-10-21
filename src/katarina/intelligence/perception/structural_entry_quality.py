"""Price-structure entry evidence: causal, explainable, research-only.

Scores compare setup quality; NOT success probabilities. No broker import,
future candle read, portfolio risk override, position sizing, or order calls.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Sequence

@dataclass(frozen=True)
class EntryEvidence:
    side: str
    playbook: str
    eligible: bool
    score: float
    evidence: tuple[str,...]
    blockers: tuple[str,...]
    next_trigger: str
    support: float | None
    resistance: float | None
    geometric_room_R: float | None
    research_only: bool = True
    live_execution_authorized: bool = False

def _get(bar,attr):
    if hasattr(bar,attr):return float(getattr(bar,attr))
    short={"open":"o","high":"h","low":"l","close":"c"}[attr]
    if hasattr(bar,short):return float(getattr(bar,short))
    return float(bar[attr])

def _atr(rows,span=14):
    if len(rows)<span+1:return None
    tr=[]
    for a,b in zip(rows[-span-1:-1],rows[-span:]):
        hi,lo,pc=_get(b,"high"),_get(b,"low"),_get(a,"close")
        tr.append(max(hi-lo,abs(hi-pc),abs(lo-pc)))
    x=sum(tr)/len(tr)
    return x if x>0 and isfinite(x) else None

def _bias(rows):
    if len(rows)<13:return 0
    atr=_atr(rows)
    if not atr:return 0
    close_now=_get(rows[-1],"close")
    close_old=_get(rows[-13],"close")
    dist=close_now-close_old
    return (1 if dist>.18*atr else -1 if dist<-.18*atr else 0)

class StructuralEntryQuality:
    """Soft scoring for structure + confirmation, hard veto for missing context.

    Defaults are research hypotheses frozen before this replay; do not
    promote based on reused 2025/2026 historical data.
    """
    def __init__(self, min_score=.64, max_spread_atr=.28):
        if not .2<=min_score<=.95 or not .02<=max_spread_atr<=.7:
            raise ValueError("invalid_entry_quality_parameters")
        self.min_score=float(min_score)
        self.max_spread_atr=float(max_spread_atr)

    def assess(self, *, side:str, playbook:str, m5:Sequence,
               m15:Sequence, h1:Sequence, spread:float,
               as_of_utc:datetime|None=None)->EntryEvidence:
        if as_of_utc is not None:
            if as_of_utc.tzinfo is None:raise ValueError("naive_decision_time")
            for frame in (m5,m15,h1):
                stamps=[getattr(row,"closed_at_utc",None) for row in frame]
                if any(x is None or x.tzinfo is None or x>as_of_utc
                       for x in stamps) or any(a>=b for a,b in zip(stamps,stamps[1:])):
                    raise ValueError("future_or_unordered_closed_frame")
        if side not in ("BUY","SELL") or not isfinite(spread) or spread<0:
            raise ValueError("invalid_side_or_spread")
        if any(len(seq)<40 for seq in (m5,m15,h1)):
            raise ValueError("insufficient_closed_history")
        direction=1 if side=="BUY" else -1
        now=m5[-1];previous=m5[-2]
        close=_get(now,"close")
        o=_get(now,"open")
        h=_get(now,"high");l=_get(now,"low")
        pc=_get(previous,"close")
        a=_atr(m5);a15=_atr(m15)
        if a is None or a15 is None:raise ValueError("invalid_atr")
        for row in (now,previous):
            op=_get(row,"open");cl=_get(row,"close")
            hi=_get(row,"high");lo=_get(row,"low")
            if not all(isfinite(x) and x>0 for x in (op,cl,hi,lo)):
                raise ValueError("nonfinite_price")
            if hi<max(op,cl) or lo>min(op,cl):
                raise ValueError("invalid_bar_geometry")
        # All channel levels exclude the current signal bar.
        pre20=m5[-21:-1];pre8=m5[-9:-1]
        lo20=min(_get(x,"low") for x in pre20)
        hi20=max(_get(x,"high") for x in pre20)
        lo8=min(_get(x,"low") for x in pre8)
        hi8=max(_get(x,"high") for x in pre8)
        m15prev=m15[-21:-1]
        support=min(_get(x,"low") for x in m15prev)
        resistance=max(_get(x,"high") for x in m15prev)
        width=max(hi20-lo20,1e-9)
        pos=(close-lo20)/width
        candle_body=abs(close-o)
        candle_range=max(h-l,1e-9)
        body_share=candle_body/candle_range
        lowwick=min(o,close)-l
        upwick=h-max(o,close)
        directed=(direction*(close-o)>0)
        progress=(direction*(close-pc)>0)
        momentum=body_share>=.53 and directed and candle_range>=.40*a
        rejection=((lowwick if direction>0 else upwick)>=max(.22*a,.85*candle_body)
                   and directed)
        previous_body=abs(_get(previous,"open")-pc)
        engulf=(directed and direction*(close-_get(previous,"open"))>0
                and direction*(o-pc)<0 and candle_body>=.85*previous_body)
        sweep=((l<lo20 and close>lo20+.05*a) if direction>0 else
               (h>hi20 and close<hi20-.05*a))
        # One-bar structural sweep can also be a false reversal; never alone.
        edge=((pos<=.40) if direction>0 else (pos>=.60))
        near_m15=(0 <= close-support <=.55*a15 if direction>0 else
                  0 <= resistance-close <=.55*a15)
        retrace=((lo8<=lo20+.32*width) if direction>0 else
                 (hi8>=hi20-.32*width))
        breakout=(close>hi20+.08*a if direction>0 else close<lo20-.08*a)
        # Retest must use an earlier CLOSED candle, not infer from current wick.
        previous_break=(_get(previous,"close")>hi20-.1*a if direction>0 else
                        _get(previous,"close")<lo20+.1*a)
        retest=(previous_break and
                ((l<=hi20+.15*a) if direction>0 else (h>=lo20-.15*a)))
        mtf15=_bias(m15);mtfh1=_bias(h1)
        score=.10
        reasons=[]
        blockers=[]
        def add(label,weight,test):
            nonlocal score
            if test:
                score+=weight;reasons.append(label)
        add("mtf_15_aligned",.13,mtf15==direction)
        add("mtf_h1_aligned",.13,mtfh1==direction)
        add("closed_candle_direction",.11,directed)
        add("positive_close_progress",.07,progress)
        add("candle_displacement",.08,momentum)
        add("rejection_wick",.14,rejection)
        add("engulfing",.13,engulf)
        add("liquidity_sweep_reclaim",.22,sweep)
        add("prior_range_edge",.09,edge)
        add("m15_zone_proximity",.08,near_m15)
        # Playbook-specific context raises/lower score rather than a
        # rigid all-indicators-must-agree checklist.
        if playbook=="TREND_PULLBACK":
            add("prior_pullback_to_m5_zone",.15,retrace)
            if not (retrace or near_m15):
                blockers.append("no_pullback_location")
            if not (rejection or engulf or sweep or momentum):
                blockers.append("no_resumption_evidence")
        elif playbook=="RANGE_FADE":
            add("range_edge_with_rejection",.16,edge and (rejection or engulf or sweep))
            if not (edge or near_m15):
                blockers.append("not_at_range_edge")
            if not (rejection or engulf or sweep):
                blockers.append("no_range_reversal_evidence")
        elif playbook=="BREAKOUT_RETEST":
            add("confirmed_prior_channel_break",.16,breakout)
            add("previously_broken_level_retested",.18,retest)
            if not (breakout and retest):
                blockers.append("breakout_retest_not_confirmed")
        elif playbook=="REVERSAL_RECLAIM":
            add("sweep_and_rejection",.22,sweep and (rejection or engulf))
            if not (sweep and (rejection or engulf)):
                blockers.append("no_structural_reversal")
        else:
            blockers.append("playbook_unsupported")
        if spread/max(a,1e-9)>self.max_spread_atr:
            blockers.append("spread_too_expensive")
        if not (directed or (rejection and progress)):
            blockers.append("no_directional_reaction")
        # Directional room towards a prior M15 channel boundary; it may be
        # NONE when the structural target is behind price or too close.
        stop_ref=min(l,lo8) if direction>0 else max(h,hi8)
        stop_buffer=.12*a+spread
        hypothetical_stop=stop_ref-direction*stop_buffer
        risk=direction*(close-hypothetical_stop)
        reward=direction*((resistance if direction>0 else support)-close)
        rr=(reward/risk) if risk>0 and reward>0 else None
        if rr is None or rr<1.25:
            blockers.append("insufficient_structural_room")
        if score<self.min_score:
            blockers.append("insufficient_combined_evidence")
        triggers={
            "no_pullback_location":"Tunggu harga menyentuh pullback/demand M5-M15.",
            "no_resumption_evidence":"Tunggu candle rejection, engulfing atau displacement searah tren.",
            "not_at_range_edge":"Tunggu area tepi sideways, hindari tengah range.",
            "no_range_reversal_evidence":"Tunggu liquidity sweep atau candle penolakan tepi range.",
            "breakout_retest_not_confirmed":"Tunggu breakout tertutup lalu retest yang jelas.",
            "no_structural_reversal":"Tunggu liquidity sweep-reclaim dan penolakan terverifikasi.",
            "spread_too_expensive":"Tunggu spread mengecil terhadap ATR.",
            "no_directional_reaction":"Tunggu harga bereaksi mengikuti arah hipotesis.",
            "insufficient_structural_room":"Tunggu lokasi masuk yang memberi RR ke struktur >= 1,25.",
            "insufficient_combined_evidence":"Tunggu setidaknya dua sumber konfirmasi struktur yang independen.",
            "playbook_unsupported":"Tunggu playbook yang memiliki verifikasi aturan.",
        }
        eligible=not blockers
        return EntryEvidence(
            side=side,playbook=playbook,eligible=eligible,
            score=round(min(1.,score),3),evidence=tuple(reasons),
            blockers=tuple(dict.fromkeys(blockers)),
            next_trigger=("Setup hipotetis valid untuk pengujian kertas, bukan izin live."
                if eligible else triggers[blockers[0]]),
            support=round(support,9),resistance=round(resistance,9),
            geometric_room_R=round(rr,3) if rr is not None else None)