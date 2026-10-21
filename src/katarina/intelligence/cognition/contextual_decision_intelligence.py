"""Causal contextual decision intelligence for KATARINA.

NOT an LLM prompt and NOT an execution system. Closed-candle MarketDecisionCard,
attributed point-in-time macro evidence, observed spread, risk constraints and
*resolved* strategy outcomes jointly determine a conditional entry hypothesis
or WAIT. Experiences are learned from resolved trades only; the absence of
reliably labeled history never turns into a fabricated advantage.

No broker, network, model-API or trading imports. No automated live promotion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isfinite, sqrt
from statistics import mean, stdev
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from katarina.intelligence.cognition.market_decision import DecisionCard
    from katarina.intelligence.news.news_intelligence import NewsContext


@dataclass(frozen=True)
class MacroEvidence:
    """Attribution and causal mechanism must be supplied by a verified feed."""
    source_id: str
    published_at_utc: datetime
    observed_at_utc: datetime
    affected_symbol: str
    favored_side: str                 # BUY / SELL / NEUTRAL / UNCERTAIN
    policy_direction: str             # explanation, not just a sentiment number
    transmission_mechanism: str       # why this affects the traded asset
    source_verified: bool
    significant: bool = True


@dataclass(frozen=True)
class ResolvedExperience:
    """Point-in-time R realized by one specific strategy and market context."""
    symbol: str
    strategy: str
    side: str
    regime: str
    signal_at_utc: datetime
    resolved_at_utc: datetime
    net_r: float                       # after REAL observed broker costs
    bid_ask_replay_verified: bool
    cost_reconciled: bool
    independently_forward_observed: bool


@dataclass(frozen=True)
class RiskSituation:
    system_healthy: bool
    broker_session_open: bool
    quote_fresh: bool
    drawdown_fraction: float           # not percentages
    realized_daily_loss_r: float
    open_positions: int
    gross_exposure_fraction: float
    max_concurrent_paper: int = 1
    max_gross_paper_fraction: float = .0025


@dataclass(frozen=True)
class ContextDecision:
    symbol: str
    analyzed_at_utc: str
    market_state: str
    direction_bias: str
    selected_method: str
    technical_setup: str
    action: str                        # WAIT or PAPER_OBSERVATION_ONLY
    conditional_side: str              # BUY/SELL/WAIT, never a broker action
    reference_entry_kind: str
    conditional_invalidation: float | None
    conditional_target: float | None
    after_spread_rr_geometry: float | None
    market_explanation: str
    macro_explanation: tuple[str, ...]
    alternative_scenario: str
    historical_context_stats: dict[str, object]
    confidence_is_profit_probability: bool
    blocking_reasons: tuple[str, ...]
    confirming_evidence: tuple[str, ...]
    next_recheck: str
    research_only: bool = True
    live_execution_authorized: bool = False
    production_risk_fraction: float = 0.0
    technical_evidence_score: float = 0.0
    directional_alignment: str = "UNASSESSED"
    directional_observations: tuple[str, ...] = ()
    directional_h1_momentum_atr: float | None = None
    directional_m15_momentum_atr: float | None = None
    pre_entry_spread_fraction_of_stop_risk: float | None = None
    pattern_semantically_confirmed: bool = False
    pattern_semantic_blockers: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def _utc(x: datetime) -> datetime:
    if not isinstance(x, datetime) or x.tzinfo is None:
        raise ValueError("timezone_aware_datetime_required")
    return x.astimezone(timezone.utc)


def _metrics(cases: Sequence[ResolvedExperience]) -> dict[str, object]:
    if not cases:
        return dict(n=0,months=0,mean_net_r=None,profit_factor=None,
                    mean_lower_95_bound=None,monthly_means={},recent_mean_r=None)
    values=[c.net_r for c in cases]
    positives=sum(v for v in values if v>0)
    negatives=-sum(v for v in values if v<0)
    buckets: dict[str,list[float]]={}
    for case in cases:
        buckets.setdefault(case.signal_at_utc.astimezone(timezone.utc).strftime("%Y-%m"),[]).append(case.net_r)
    # A conservative lower mean bound is only a descriptive normal approximation;
    # it is NOT calibrated predictive uncertainty and NOT an executable probability.
    low=(mean(values)-1.96*stdev(values)/sqrt(len(values))
         if len(values)>=2 else None)
    return dict(n=len(values),months=len(buckets),mean_net_r=round(mean(values),6),
                profit_factor=round(positives/negatives,5) if negatives else None,
                mean_lower_95_bound=round(low,6) if low is not None else None,
                monthly_means={k:round(mean(v),6) for k,v in sorted(buckets.items())},
                recent_mean_r=round(mean(values[-min(20,len(values)):]),6))


class ContextualDecisionIntelligence:
    """Reason over market structure, external evidence, and resolved experience.

    No training or dynamic optimization against the current candle.
    Hard blockers override all positive scores. An LLM explanation can NEVER
    override a blocker or invent a macro source, trade or outcome.
    """
    def __init__(self, *, max_spread_atr: float = .22,
                 min_net_rr: float = 1.25, min_forward_trades: int = 45):
        if not 0 < max_spread_atr < 1 or min_net_rr < 1 or min_forward_trades < 30:
            raise ValueError("invalid_contextual_policy")
        self.max_spread_atr=max_spread_atr
        self.min_net_rr=min_net_rr
        self.min_forward_trades=min_forward_trades

    def evaluate(
        self, *, card: DecisionCard, as_of_utc: datetime,
        news: NewsContext, macro: Sequence[MacroEvidence],
        experience: Sequence[ResolvedExperience], risk: RiskSituation,
        observed_spread: float, m15_atr: float,
    ) -> ContextDecision:
        now=_utc(as_of_utc)
        reasons=[]
        support=[]
        notes=[]
        if not card.symbol or card.analyzed_at_utc!=as_of_utc.isoformat():
            reasons.append("snapshot_identity_or_clock_mismatch")
        symbol=card.symbol
        if card.market_state in ("UNKNOWN","TRANSITION","VOLATILITY_SHOCK"):
            reasons.append("uncertain_or_shock_regime")
        if not risk.system_healthy:
            reasons.append("system_unhealthy")
        if not risk.broker_session_open:
            reasons.append("broker_session_closed")
        if not risk.quote_fresh:
            reasons.append("stale_quote")
        if not isfinite(observed_spread) or observed_spread<0 or not isfinite(m15_atr) or m15_atr<=0:
            reasons.append("invalid_broker_cost_or_atr")
            ratio=None
        else:
            ratio=observed_spread/m15_atr
            if ratio>self.max_spread_atr:
                reasons.append("spread_exceeds_M15_volatility_budget")
            else:
                support.append("broker_cost_below_volatility_ceiling")
        if (not isfinite(risk.drawdown_fraction) or risk.drawdown_fraction<0
                or not isfinite(risk.realized_daily_loss_r)
                or not isfinite(risk.gross_exposure_fraction)
                or risk.gross_exposure_fraction<0
                or risk.open_positions<0):
            reasons.append("invalid_risk_snapshot")
        else:
            if risk.drawdown_fraction>=.04:
                reasons.append("drawdown_pause")
            if risk.realized_daily_loss_r<=-2:
                reasons.append("daily_loss_pause")
            if risk.open_positions>=risk.max_concurrent_paper:
                reasons.append("concurrent_paper_limit")
            if risk.gross_exposure_fraction>=risk.max_gross_paper_fraction:
                reasons.append("paper_exposure_cap")

        # Separate chart direction hypothesis from actual permission to entry.
        # Show opposing evidence as well as confirmation in the SAME existing
        # ContextDecision API, rather than hiding it in a second Brain.
        if card.directional_alignment!="UNASSESSED":
            support.append("directional_alignment:"+card.directional_alignment)
        if card.directional_alignment=="H1_M15_STRONG_OPPOSITION_WAIT":
            reasons.append("H1_M15_directional_contradiction")
        technical=card.technical_signal
        if technical not in ("BUY","SELL"):
            reasons.append("no_confirmed_closed_candle_entry")
        if card.evidence_score<.62 or card.evidence_not_probability is not True:
            reasons.append("technical_evidence_not_sufficient")
        if (card.rr_after_spread_estimate is None
                or card.rr_after_spread_estimate<self.min_net_rr):
            reasons.append("risk_reward_geometry_not_favorable")
        if not card.strategy or card.strategy=="OBSERVE":
            reasons.append("no_market_appropriate_playbook")
        if card.invalidation_level is None or card.primary_target is None:
            reasons.append("missing_structural_exit_plan")
        else:
            # Direction and invalidation geometry must be correctly ordered.
            if technical=="BUY" and not (card.invalidation_level<card.primary_target):
                reasons.append("buy_structure_geometry_invalid")
            if technical=="SELL" and not (card.invalidation_level>card.primary_target):
                reasons.append("sell_structure_geometry_invalid")

        if not news.ready or news.matched_items<1 or news.source_count<1:
            reasons.append("no_verified_relevant_news")
        if news.blackout:
            reasons.append("high_impact_news_blackout")
        if not isfinite(news.risk_score) or news.risk_score>.8:
            reasons.append("macro_event_risk_too_high")

        accepted=[]
        seen_sources=set()
        for item in macro:
            try:
                published=_utc(item.published_at_utc)
                observed=_utc(item.observed_at_utc)
            except ValueError:
                reasons.append("macro_missing_credible_clock")
                continue
            if published>now or observed>now or observed<published:
                reasons.append("future_or_unobserved_macro_information")
                continue
            if (item.affected_symbol!=symbol or not item.source_verified
                    or item.favored_side not in ("BUY","SELL","NEUTRAL","UNCERTAIN")
                    or not item.policy_direction.strip()
                    or not item.transmission_mechanism.strip()
                    or not item.source_id.strip()):
                continue
            if (now-published).total_seconds()>6*3600:
                continue
            accepted.append(item)
            seen_sources.add(item.source_id)
            notes.append(item.source_id+": "+item.policy_direction+
                         " → "+item.transmission_mechanism+
                         " ["+item.favored_side+"]")
        if not accepted:
            reasons.append("macro_policy_transmission_not_verified")
        if any(x.significant and x.favored_side=="UNCERTAIN" for x in accepted):
            reasons.append("material_macro_direction_uncertain")
        directional={x.favored_side for x in accepted
                     if x.significant and x.favored_side in ("BUY","SELL")}
        if len(directional)>1:
            reasons.append("contradictory_macro_direction")
        elif technical in ("BUY","SELL") and directional and technical not in directional:
            reasons.append("macro_technical_direction_conflict")
        elif technical in directional:
            support.append("attributed_macro_aligned_with_technical")
        else:
            support.append("attributed_macro_neutral_or_not_directional")

        # Never use results from the future, unfinalized trades or other market
        # regimes. Fail closed on a corrupted ledger rather than filtering it
        # into a misleading profitable subset.
        valid_history=[]
        for case in experience:
            try:
                start=_utc(case.signal_at_utc)
                end=_utc(case.resolved_at_utc)
                if (start>=end or end>=now or not isfinite(case.net_r)
                        or abs(case.net_r)>100):
                    raise ValueError("unresolved_or_future_result")
            except (ValueError,TypeError):
                reasons.append("outcome_ledger_violates_point_in_time")
                valid_history=[]
                break
            if (case.symbol,case.strategy,case.side,case.regime)==(
                    symbol,card.strategy,technical,card.market_state):
                valid_history.append(case)
        valid_history.sort(key=lambda x:x.resolved_at_utc)
        stats=_metrics(valid_history)
        forward=[x for x in valid_history
                 if x.independently_forward_observed and x.bid_ask_replay_verified
                 and x.cost_reconciled]
        forward_stats=_metrics(forward)
        stats["cost_spread_to_m15_atr"]=round(ratio,6) if ratio is not None else None
        stats["verified_forward"] = forward_stats
        # Historical V6-V10 results are explicitly not independently forward.
        # Never give them paper-readiness just by counting more backtests.
        if len(forward)<self.min_forward_trades:
            reasons.append("insufficient_verified_forward_experience")
        elif (forward_stats["months"]<3 or any(v<=0 for v in forward_stats["monthly_means"].values())
                or forward_stats["mean_net_r"]<=.10 or
                forward_stats["profit_factor"] is None or forward_stats["profit_factor"]<1.20
                or forward_stats["mean_lower_95_bound"] is None or
                forward_stats["mean_lower_95_bound"]<=0
                or forward_stats["recent_mean_r"]<=0):
            reasons.append("resolved_forward_performance_not_stable")
        else:
            support.append("causal_forward_performance_gate_passed")

        if card.evidence_score>=.62:
            support.append("multi_timeframe_technical_evidence_present")
        if card.strategy:
            support.append("conditional_strategy:"+card.strategy)
        # This flag is intentionally never supplied to the production
        # Risk Governor or used to authorize broker order placement.
        action="WAIT" if reasons else "PAPER_OBSERVATION_ONLY"
        if reasons:
            next_check=("Perbarui candle tertutup, kutipan broker, sumber kebijakan, "
                        "dan catatan outcome forward yang sudah selesai; "
                        "jangan buka posisi selama syarat belum terpenuhi.")
        else:
            next_check=("Catat sinyal paper secara independen, evaluasi hasil "
                        "sesudah posisi simulasi ditutup; tidak ada order live.")
        return ContextDecision(
            symbol=symbol,analyzed_at_utc=now.isoformat(),
            market_state=card.market_state,direction_bias=card.directional_bias,
            technical_evidence_score=card.evidence_score,
            directional_alignment=card.directional_alignment,
            directional_observations=card.directional_observations,
            directional_h1_momentum_atr=card.directional_h1_momentum_atr,
            directional_m15_momentum_atr=card.directional_m15_momentum_atr,
            pre_entry_spread_fraction_of_stop_risk=(
                card.pre_entry_spread_fraction_of_stop_risk),
            pattern_semantically_confirmed=card.pattern_semantically_confirmed,
            pattern_semantic_blockers=card.pattern_semantic_blockers,
            selected_method=card.strategy,technical_setup=technical,
            action=action,conditional_side=technical if technical in ("BUY","SELL") else "WAIT",
            reference_entry_kind="CLOSED_BAR_CONFIRMATION_NEXT_BAR_PAPER_ONLY",
            conditional_invalidation=card.invalidation_level,
            conditional_target=card.primary_target,
            after_spread_rr_geometry=card.rr_after_spread_estimate,
            market_explanation=card.market_explanation,
            macro_explanation=tuple(notes),
            alternative_scenario=card.alternative_scenario,
            historical_context_stats=stats,
            confidence_is_profit_probability=False,
            blocking_reasons=tuple(dict.fromkeys(reasons)),
            confirming_evidence=tuple(dict.fromkeys(support)),
            next_recheck=next_check,
        )
