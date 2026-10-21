"""KATARINA Market Decision Brain V3 -- interpretable, causal, read-only.

One symbol -> explain market, direction, probable conditional path, playbook,
independent technical setup, WAIT reasons and precise re-evaluation trigger.
Evidence score is NOT success probability. No MT5/execution import.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from typing import TYPE_CHECKING, Mapping, Sequence

from katarina.intelligence.cognition.market_decision_pipeline import (
    MarketDecisionPipeline, SensorCandle,
)

if TYPE_CHECKING:  # annotation-only; avoids import cycles at runtime
    from katarina.intelligence.cognition.contextual_decision_intelligence import (
        ContextDecision, MacroEvidence, ResolvedExperience, RiskSituation)
    from katarina.intelligence.news.news_intelligence import NewsContext

@dataclass(frozen=True)
class DecisionCard:
    symbol: str
    analyzed_at_utc: str
    market_phase: str
    directional_bias: str
    market_state: str
    evidence_score: float
    evidence_not_probability: bool
    market_explanation: str
    primary_scenario: str
    alternative_scenario: str
    primary_target: float | None
    invalidation_level: float | None
    target_kind: str
    strategy: str
    technical_signal: str
    decision: str
    strategy_validated: bool
    rr_after_spread_estimate: float | None
    evidence: tuple[str, ...]
    blockers: tuple[str, ...]
    next_trigger: str
    research_only: bool = True
    live_execution_authorized: bool = False
    directional_alignment: str = "UNASSESSED"
    directional_observations: tuple[str, ...] = ()
    directional_h1_momentum_atr: float | None = None
    directional_m15_momentum_atr: float | None = None
    pre_entry_spread_fraction_of_stop_risk: float | None = None
    pattern_semantically_confirmed: bool = False
    pattern_semantic_blockers: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


class MarketDecisionBrain:
    """Weighted technical context + hard controls.

    Hard controls: causal/valid candles, current quote/session, news verification,
    broker spread, actually validated pair/playbook, risk gate.
    Soft evidence: trend structure, candle confirmation, existing proposal,
    proximity to meaningful price levels, room to objective target.
    """

    def __init__(self, minimum_evidence_score: float = .62,
                 max_spread_atr: float = .34, minimum_rr: float = 1.25,
                 max_spread_initial_risk_fraction: float = .20):
        if (not 0 < minimum_evidence_score < 1 or
            not 0 < max_spread_atr < 1 or minimum_rr <= 0 or
            not 0 < max_spread_initial_risk_fraction <= .25):
            raise ValueError("invalid_market_decision_parameters")
        self.observer = MarketDecisionPipeline()
        self.min_score = minimum_evidence_score
        self.max_spread_atr = max_spread_atr
        self.min_rr = minimum_rr
        # Engineering safety budget, NOT an optimized profitable parameter.
        # Spread at the last closed M5 candle may be stale at next entry;
        # actual next-tick costs are separately checked when available.
        self.max_spread_initial_risk_fraction=max_spread_initial_risk_fraction

    @staticmethod
    def _atr(rows: Sequence[SensorCandle], n: int = 14) -> float:
        sample = rows[-n-1:]
        if len(sample) < n+1:
            return 0.
        changes = [max(b.high-b.low, abs(b.high-a.close), abs(b.low-a.close))
                   for a,b in zip(sample,sample[1:])]
        return sum(changes)/len(changes)

    @staticmethod
    def _card_wait(symbol: str, now: datetime, reasons: Sequence[str]) -> DecisionCard:
        return DecisionCard(symbol,now.isoformat(),"TIDAK TERBACA","TIDAK PASTI",
                            "UNKNOWN",0.,True,"Data belum cukup untuk analisis yang dapat dipercaya.",
                            "Tunggu data harga valid.","Jangan membuka posisi sampai data pulih.",
                            None,None,"none","OBSERVE","WAIT","WAIT",False,None,
                            tuple(reasons),tuple(reasons),"Periksa data OHLC, waktu candle, dan koneksi broker.")

    @staticmethod
    def _phase(state: str) -> tuple[str,str]:
        mapping={
            "TREND_UP":("TREND NAIK","BULLISH"),
            "TREND_DOWN":("TREND TURUN","BEARISH"),
            "PULLBACK_UP":("KOREKSI DI DALAM TREND NAIK","BULLISH BERSYARAT"),
            "PULLBACK_DOWN":("REBOUND DI DALAM TREND TURUN","BEARISH BERSYARAT"),
            "SIDEWAYS":("KONSOLIDASI / RANGE","SIDEWAYS"),
            "BREAKOUT_UP":("BREAKOUT NAIK","BULLISH BERSYARAT"),
            "BREAKOUT_DOWN":("BREAKOUT TURUN","BEARISH BERSYARAT"),
            "REVERSAL_UP":("REVERSE NAIK TERKONFIRMASI STRUKTUR","BULLISH BERSYARAT"),
            "REVERSAL_DOWN":("REVERSE TURUN TERKONFIRMASI STRUKTUR","BEARISH BERSYARAT"),
            "VOLATILITY_SHOCK":("GUNCANGAN VOLATILITAS","TIDAK PASTI"),
            "TRANSITION":("TRANSISI / KONFLIK TIMEFRAME","TIDAK PASTI"),
            "UNKNOWN":("BELUM TERKLASIFIKASI","TIDAK PASTI"),
        }
        return mapping.get(state,("TIDAK TERBACA","TIDAK PASTI"))

    def evaluate(
        self, *,
        symbol: str, candles: Mapping[str,Sequence[SensorCandle]],
        as_of_utc: datetime, actual_spread: float,
        broker_session_open: bool, data_fresh: bool,
        news_blackout: bool, news_context_verified: bool = False,
        strategy_evidence: Mapping[tuple[str,str,str],bool] | None = None,
        risk_approved_for_paper: bool = False,
    ) -> DecisionCard:
        if not symbol or as_of_utc.tzinfo is None:
            return self._card_wait(symbol,as_of_utc,("invalid_symbol_or_time",))
        if any(tf not in candles or len(candles[tf]) < 55 for tf in ("M5","M15","H1")):
            return self._card_wait(symbol,as_of_utc,("insufficient_closed_market_history",))
        observation=self.observer.evaluate(
            symbol=symbol,candles=candles,as_of_utc=as_of_utc,
            actual_spread=actual_spread,broker_session_open=broker_session_open,
            data_fresh=data_fresh,news_blackout=news_blackout,
            news_context_verified=news_context_verified)
        state=observation.market_state
        if state=="UNKNOWN":
            return self._card_wait(symbol,as_of_utc,observation.reasons)
        m5,m15,h1=(candles[t] for t in ("M5","M15","H1"))
        atr=self._atr(m15);latest=m5[-1];price=latest.close
        if atr<=0 or not all(isfinite(x) and x>0 for x in
             (price,atr,latest.open,latest.high,latest.low)):
            return self._card_wait(symbol,as_of_utc,("invalid_price_or_atr",))
        phase,bias=self._phase(state)
        hh=max(b.high for b in h1[-31:-1])
        ll=min(b.low for b in h1[-31:-1])
        mhigh=max(b.high for b in m15[-29:-1])
        mlow=min(b.low for b in m15[-29:-1])
        width=max(mhigh-mlow,atr*.5)
        channel_position=(price-mlow)/width
        bull=latest.close>latest.open
        bear=latest.close<latest.open
        span=max(latest.high-latest.low,1e-10)
        body=abs(latest.close-latest.open)/span
        low_wick=(min(latest.open,latest.close)-latest.low)/span
        high_wick=(latest.high-max(latest.open,latest.close))/span
        last_m15=m15[-1]
        movement_m15=(last_m15.close-m15[-5].close)/max(atr,1e-10)
        # Directional context does not mean an actual trade is allowed.
        sign=1 if state.endswith("_UP") else -1 if state.endswith("_DOWN") else 0
        evidence=["regime:"+state,"playbook:"+observation.playbook]
        if state=="SIDEWAYS":
            if channel_position<=.25 and (bull or low_wick>.38):
                sign=1;evidence.append("range_lower_edge_with_buy_rejection")
            elif channel_position>=.75 and (bear or high_wick>.38):
                sign=-1;evidence.append("range_upper_edge_with_sell_rejection")
            else:
                evidence.append("range_middle_no_edge_advantage")
        if sign==0 and state=="VOLATILITY_SHOCK":
            evidence.append("volatility_shock_wait_for_stabilization")
        elif sign==0:
            evidence.append("timeframe_disagreement_or_no_direction")

        # Infer nearest *prior* structural boundary. Never label ATR projection as S/R.
        if sign>0:
            level=hh if hh>price else None
            target=level if level is not None else price+2*atr
            target_kind="prior_H1_resistance" if level is not None else "ATR_projection_not_confirmed_resistance"
            # Invalidate under the most recent *prior* M15 micro-structure,
            # not the entire 28-bar range (which is often too distant).
            invalid=min(b.low for b in m15[-11:-1])-.12*atr
            primary=f"Jika support bertahan dan buyer menguat, harga berpeluang menuju {target:.6f}."
            alternative=f"Jika harga turun melewati {invalid:.6f}, bias naik batal; evaluasi ulang arah."
        elif sign<0:
            level=ll if ll<price else None
            target=level if level is not None else price-2*atr
            target_kind="prior_H1_support" if level is not None else "ATR_projection_not_confirmed_support"
            invalid=max(b.high for b in m15[-11:-1])+.12*atr
            primary=f"Jika supply bertahan dan seller menguat, harga berpeluang menuju {target:.6f}."
            alternative=f"Jika harga naik melewati {invalid:.6f}, bias turun batal; evaluasi ulang arah."
        else:
            target=hh
            invalid=ll
            target_kind="range_H1_upper_boundary"
            primary=f"Belum ada arah dominan. Pantau batas range sekitar {ll:.6f}–{hh:.6f}."
            alternative="Tunggu penutupan candle melewati batas range dan amati apakah break valid."
        if sign==1 and invalid>=price:
            invalid=price-1.2*atr
        if sign==-1 and invalid<=price:
            invalid=price+1.2*atr
        rr=None
        provisional_cost_risk=None
        if sign and isfinite(actual_spread) and actual_spread>=0:
            distance=abs(price-invalid)
            reward=(target-price)*sign-actual_spread
            rr=round(max(0.,reward)/max(distance+actual_spread,1e-10),3)
            provisional_cost_risk=actual_spread/max(
                distance+actual_spread,1e-10)
            evidence.append("spread_to_structural_risk_ratio:"+
                            f"{provisional_cost_risk:.3f}")
        # Soft, interpretable evidence; no false conversion to win probability.
        score=.22
        if sign:score+=.16
        if sign and (bull if sign>0 else bear):
            score+=.12;evidence.append("M5_closed_candle_confirms_side")
        if sign and ((movement_m15>0) if sign>0 else (movement_m15<0)):
            score+=.12;evidence.append("M15_momentum_confirms_side")
        if body>.55 and sign and (bull if sign>0 else bear):
            score+=.08;evidence.append("strong_body_candle")
        if observation.setup_ready and observation.potential_action==("BUY" if sign>0 else "SELL"):
            score+=.16;evidence.append("existing_closed_bar_setup_ready")
        if state in ("BREAKOUT_UP","BREAKOUT_DOWN","REVERSAL_UP","REVERSAL_DOWN"):
            score+=.10;evidence.append("structural_direction_confirmed")
        elif state=="SIDEWAYS" and sign:
            score+=.10;evidence.append("range_edge_rejection")
        if rr is not None and rr>=self.min_rr:
            score+=.10;evidence.append("room_to_structural_target_after_spread")
        score=round(min(1.,score),3)
        # Independent two-sided closed-bar assessment. Explicitly expose
        # evidence AGAINST BUY and AGAINST SELL; this is NOT a predicted
        # success probability or independent model that places orders.
        direction=None
        direction_failure=False
        if sign:
            from katarina.intelligence.perception.directional_consensus import (
                assess_direction,
            )
            try:
                direction=assess_direction(
                    candles=candles,as_of_utc=as_of_utc,
                    side=("BUY" if sign>0 else "SELL"),regime=state)
                evidence.append("directional_alignment:"+direction.verdict)
                evidence.extend(direction.supports)
                evidence.extend("counter_evidence:"+x for x in direction.challenges)
            except (ValueError,TypeError,OverflowError):
                direction_failure=True
                evidence.append("directional_evidence_unavailable_fail_closed")
        # A playbook name must correspond to a real CLOSED-BAR event.
        # Reuse the already computed native semantic setup if matching
        # the current side; otherwise ask the same native validator.
        # This is a VETO ONLY, not a second policy or new entry model.
        semantic=None
        semantic_unverifiable=False
        strategy=observation.playbook
        if sign and strategy!="OBSERVE":
            try:
                proposed_side="BUY" if sign>0 else "SELL"
                semantic=observation.semantic_setup
                if semantic is None or semantic.side!=proposed_side:
                    semantic=self.observer.semantic_validator.assess(
                        side=proposed_side,playbook=strategy,
                        m5=m5,m15=m15,h1=h1,spread=actual_spread,
                        as_of_utc=as_of_utc,
                    )
                if semantic.pattern_confirmed:
                    evidence.append("native_playbook_price_action_verified")
                    evidence.extend("semantic_support:"+x for x in semantic.evidence)
                else:
                    evidence.append("native_playbook_pattern_unconfirmed")
                    evidence.extend("semantic_missing:"+x for x in semantic.blockers)
            except (ValueError,TypeError,OverflowError):
                semantic_unverifiable=True
                evidence.append("semantic_setup_unverifiable_fail_closed")
        # Distinguish directional *bias* from a technically actionable setup.
        # Soft evidence is weighted, but minimum net geometry is non-negotiable.
        signal=("BUY" if sign>0 else "SELL" if sign<0 else "WAIT") if (
            score>=self.min_score and rr is not None and rr>=self.min_rr) else "WAIT"
        blockers=[]
        if sign and strategy!="OBSERVE" and (
                semantic_unverifiable or semantic is None or
                not semantic.pattern_confirmed):
            blockers.append("playbook_semantics_not_confirmed")
            if semantic is not None:
                blockers.extend("semantic:"+x for x in semantic.blockers)
        if direction_failure:
            blockers.append("directional_evidence_invalid_or_future")
        if direction is not None and direction.veto_strong_contradiction:
            blockers.append("H1_M15_strongly_contradict_candidate_side")
        if not data_fresh or not broker_session_open:
            blockers.append("market_closed_or_data_stale")
        if not isfinite(actual_spread) or actual_spread<0 or actual_spread/atr>self.max_spread_atr:
            blockers.append("spread_too_high_for_volatility")
        if (provisional_cost_risk is not None and
            provisional_cost_risk>self.max_spread_initial_risk_fraction):
            blockers.append("broker_spread_consumes_excess_structural_risk")
        if news_blackout:
            blockers.append("high_impact_news_blackout")
        if not news_context_verified:
            blockers.append("news_context_unverified")
        if score<self.min_score:
            blockers.append("insufficient_technical_evidence")
        if not sign:
            blockers.append("direction_or_range_edge_unclear")
        if rr is None or rr<self.min_rr:
            blockers.append("not_enough_room_for_risk_reward")
        if strategy=="OBSERVE":
            blockers.append("no_supported_strategy_for_regime")
        verified=bool((strategy_evidence or {}).get((symbol,strategy,signal),False))
        if not verified:
            blockers.append("pair_strategy_edge_not_validated")
        if not risk_approved_for_paper:
            blockers.append("paper_risk_governor_not_approved")
        if not sign:
            next_trigger="Tunggu alignment M15/H1 atau reaksi jelas pada batas range."
        elif score<self.min_score:
            next_trigger="Tunggu candle tertutup yang menguatkan arah dan konfirmasi M15."
        elif rr is None or rr<self.min_rr:
            next_trigger="Tunggu pullback atau level target berikutnya agar reward mencukupi biaya dan stop."
        elif not verified:
            next_trigger="Validasi playbook khusus pair ini menggunakan sampel baru, spread riil, dan forward-demo."
        else:
            next_trigger="Perbarui setelah candle M5 tertutup berikutnya dan seluruh hard gate diverifikasi."
        # Strong directional opposition can only REDUCE permission:
        # never create an extra BUY/SELL from this assessment.
        if (direction_failure or
            (direction and direction.veto_strong_contradiction) or
            (sign and strategy!="OBSERVE" and
             (semantic_unverifiable or semantic is None or
              not semantic.pattern_confirmed)) or
            (provisional_cost_risk is not None and
             provisional_cost_risk>self.max_spread_initial_risk_fraction)):
            signal="WAIT"
        decision=signal if signal!="WAIT" and not blockers else "WAIT"
        description=(f"{phase}; harga terakhir {price:.6f}; posisi pada channel M15 "
                     f"{channel_position:.0%}. Bukti teknikal {score:.2f}, bukan probabilitas profit.")
        return DecisionCard(symbol,as_of_utc.isoformat(),phase,bias,state,score,True,
                            description,primary,alternative,round(target,8) if target is not None else None,
                            round(invalid,8) if invalid is not None else None,target_kind,
                            strategy,signal,decision,verified,rr,tuple(evidence),
                            tuple(blockers),next_trigger,
                            directional_alignment=(direction.verdict if direction
                                                   else "UNASSESSED"),
                            directional_observations=(direction.supports+
                                                       direction.challenges if direction
                                                       else ()),
                            directional_h1_momentum_atr=(
                                direction.h1_momentum_atr if direction else None),
                            directional_m15_momentum_atr=(
                                direction.m15_momentum_atr if direction else None),
                            pre_entry_spread_fraction_of_stop_risk=(
                                round(provisional_cost_risk,5)
                                if provisional_cost_risk is not None else None),
                            pattern_semantically_confirmed=bool(
                                semantic and semantic.pattern_confirmed),
                            pattern_semantic_blockers=(
                                semantic.blockers if semantic else (
                                ("native_semantic_evidence_unavailable",)
                                if semantic_unverifiable else ())))

    def evaluate_contextually(
        self, *, symbol: str, candles: Mapping[str,Sequence[SensorCandle]],
        as_of_utc: datetime, actual_spread: float,
        news_context: "NewsContext",
        macro_evidence: Sequence["MacroEvidence"],
        resolved_experience: Sequence["ResolvedExperience"],
        risk_situation: "RiskSituation",
    ) -> "ContextDecision":
        """Native data-based reasoning: market + macro + execution + memory.

        Additive research-only interface. Existing evaluate(), trading engine
        and Risk Governor behavior remain unchanged. No model/LLM order path.
        """
        from katarina.intelligence.cognition.contextual_decision_intelligence import (
            ContextualDecisionIntelligence,
        )
        news_verified=(news_context.ready and news_context.matched_items>0
                       and news_context.source_count>0)
        card=self.evaluate(
            symbol=symbol,candles=candles,as_of_utc=as_of_utc,
            actual_spread=actual_spread,
            broker_session_open=risk_situation.broker_session_open,
            data_fresh=risk_situation.quote_fresh,
            news_blackout=news_context.blackout,
            news_context_verified=news_verified,
            # Do not inject self-reported strategy profitability or bypass
            # the existing production-independent readiness restrictions.
            strategy_evidence=None,risk_approved_for_paper=False,
        )
        atr=self._atr(candles.get("M15",()))
        return ContextualDecisionIntelligence().evaluate(
            card=card,as_of_utc=as_of_utc,news=news_context,
            macro=macro_evidence,experience=resolved_experience,
            risk=risk_situation,observed_spread=actual_spread,m15_atr=atr,
        )
