"""Causal read-only market-to-decision pipeline for KATARINA.

Consumes CLOSED M5/M15/H1 candles. Indicator values and price levels are computed
from those candles only. Fibonacci and broker tick-volume VWAP are descriptive
context, never stand-alone trade signals or evidence of predictive accuracy.
No MT5 trading API or execution module is imported here.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Mapping, Sequence

from katarina.engines.adaptive_risk import AdaptiveRiskProfile
from katarina.intelligence.adaptive_brain_v2 import KatarinaAdaptiveBrainV2
from katarina.intelligence.closed_swing_structure import ClosedBar
from katarina.intelligence.structural_entry_quality import (
    EntryEvidence, StructuralEntryQuality,
)
from katarina.intelligence.structure_exit_plan import (
    StructuralExitPlan, StructuralExitPlanner,
)
from katarina.intelligence.semantic_setup_truth import (
    SemanticSetup, CausalSetupValidator,
)
from katarina.intelligence.explainable_market_decision import (
    AdaptiveMarketDecisionAdvisor, MarketDecision,
)


_PERIOD = {"M5": timedelta(minutes=5), "M15": timedelta(minutes=15),
           "H1": timedelta(hours=1)}


@dataclass(frozen=True)
class SensorCandle:
    closed_at_utc: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: float | None = None

    def to_bar(self) -> ClosedBar:
        return ClosedBar(self.closed_at_utc, self.open, self.high, self.low, self.close)


@dataclass(frozen=True)
class DecisionObservation:
    symbol: str
    action: str
    market_state: str
    playbook: str
    reasons: tuple[str, ...]
    tools: dict[str, object]
    risk_fraction_reference: float | None
    research_only: bool = True
    live_execution_authorized: bool = False
    potential_action: str = "WAIT"
    setup_ready: bool = False
    decision_detail: MarketDecision | None = None
    entry_quality: EntryEvidence | None = None
    experimental_exit_plan: StructuralExitPlan | None = None
    semantic_setup: SemanticSetup | None = None


def _frame(candles: Sequence[SensorCandle]):
    """ATR14, causal Wilder ADX14, and 12-bar directional efficiency."""
    from katarina.intelligence.adaptive_regime import ClosedFrame
    tr, pdm, mdm = [], [], []
    for a, b in zip(candles, candles[1:]):
        tr.append(max(b.high-b.low, abs(b.high-a.close), abs(b.low-a.close)))
        up, down = b.high-a.high, a.low-b.low
        pdm.append(up if up > down and up > 0 else 0.0)
        mdm.append(down if down > up and down > 0 else 0.0)
    n = 14
    atr, plus, minus = map(lambda xs: sum(xs[:n])/n, (tr, pdm, mdm))
    dx = []
    for i in range(n - 1, len(tr)):
        if i > n - 1:
            atr = (atr*(n-1)+tr[i])/n
            plus = (plus*(n-1)+pdm[i])/n
            minus = (minus*(n-1)+mdm[i])/n
        pdi, mdi = (100*plus/atr if atr else 0), (100*minus/atr if atr else 0)
        dx.append(100*abs(pdi-mdi)/(pdi+mdi) if (pdi+mdi) else 0.0)
    adx = sum(dx[:n])/n
    for x in dx[n:]:
        adx = ((n-1)*adx+x)/n
    c = [b.close for b in candles[-13:]]
    drift = c[-1]-c[0]
    distance = sum(abs(b-a) for a,b in zip(c,c[1:]))
    er = abs(drift)/distance if distance else 0.0
    direction = 1 if drift > .15*atr else -1 if drift < -.15*atr else 0
    return ClosedFrame(direction, adx, min(1.0,er), atr,
                       candles[-1].closed_at_utc)


def _tools(m5: Sequence[SensorCandle],
           m15: Sequence[SensorCandle], h1_direction: int) -> dict[str, object]:
    # Last 20 closed M15 candles: objective extrema, no intrabar pivots.
    prior = m15[-21:-1]
    lo, hi = min(x.low for x in prior), max(x.high for x in prior)
    price = m5[-1].close
    span = hi-lo
    fibs = {}
    if span > 0 and h1_direction:
        # Pullback of prior range in prevailing direction, not a verified swing.
        fibs = {str(p): round(hi-span*p if h1_direction > 0 else lo+span*p, 8)
                for p in (.382, .5, .618)}
    vwap = None
    # Rolling observed-window proxy, NOT a full-day or exchange-wide VWAP.
    window = m5[-20:]
    usable = [x for x in window if x.tick_volume is not None and x.tick_volume > 0]
    if len(usable) == len(window) and len(window) == 20:
        total = sum(x.tick_volume for x in usable)
        vwap = sum(((x.high+x.low+x.close)/3)*x.tick_volume for x in usable)/total
    return {
        "fib_retracements": fibs,
        "fib_reference": "M15_previous_20_bar_range_not_confirmed_pivots",
        "broker_tick_volume_vwap": round(vwap, 8) if vwap is not None else None,
        "vwap_source": "ROLLING20_M5_BROKER_TICK_VOLUME_PROXY_NOT_EXCHANGE_VOLUME",
        "relative_tick_volume": (
            round(m5[-1].tick_volume / (sum(x.tick_volume for x in m5[-21:-1])/20), 4)
            if len(m5) >= 21 and m5[-1].tick_volume is not None
            and all(x.tick_volume is not None and x.tick_volume > 0 for x in m5[-21:-1])
            and sum(x.tick_volume for x in m5[-21:-1]) > 0 else None
        ),
        "price_to_vwap": round(price-vwap, 8) if vwap is not None else None,
    }


class MarketDecisionPipeline:
    """Offline/research advisory. Decisions never bypass an execution governor."""

    def __init__(self):
        self.brain = KatarinaAdaptiveBrainV2()
        self.advisor = AdaptiveMarketDecisionAdvisor()
        self.entry_advisor = StructuralEntryQuality()
        self.exit_planner = StructuralExitPlanner()
        self.semantic_validator = CausalSetupValidator()

    @staticmethod
    def _wait(symbol: str, reason: str) -> DecisionObservation:
        return DecisionObservation(symbol, "WAIT", "UNKNOWN", "OBSERVE",
                                   (reason,), {}, None)

    def evaluate(
        self, *, symbol: str, candles: Mapping[str, Sequence[SensorCandle]],
        as_of_utc: datetime, actual_spread: float,
        broker_session_open: bool, data_fresh: bool, news_blackout: bool,
        news_context_verified: bool = False,
        active_capital_native: float | None = None,
        account_currency: str = "USD",
        use_structural_entry_gate: bool = False,
        use_semantic_setup_gate: bool = False,
        instrument_point: float | None = None,
    ) -> DecisionObservation:
        if not symbol or as_of_utc.tzinfo is None:
            return self._wait(symbol, "missing_symbol_or_aware_time")
        if not isfinite(actual_spread) or actual_spread < 0:
            return self._wait(symbol, "invalid_spread")
        try:
            if any(k not in candles or len(candles[k]) < 55 for k in _PERIOD):
                return self._wait(symbol, "insufficient_multitimeframe_history")
            frames = {}
            for tf in _PERIOD:
                rows = candles[tf]
                last_time = None
                for c in rows:
                    numbers = (c.open, c.high, c.low, c.close)
                    if (c.closed_at_utc.tzinfo is None or
                        c.closed_at_utc.astimezone(timezone.utc) > as_of_utc.astimezone(timezone.utc)
                        or (last_time is not None and c.closed_at_utc <= last_time) or
                        not all(isfinite(x) and x > 0 for x in numbers) or
                        c.high < max(c.open, c.close) or c.low > min(c.open, c.close) or
                        (c.tick_volume is not None and
                         (not isfinite(c.tick_volume) or c.tick_volume < 0))):
                        return self._wait(symbol, "invalid_or_future_candle")
                    last_time = c.closed_at_utc
                # An expected market-open snapshot must be current; no weekend stale action.
                if (data_fresh and broker_session_open and
                    (as_of_utc - rows[-1].closed_at_utc) > _PERIOD[tf]*2):
                    return self._wait(symbol, "stale_" + tf + "_data")
                frames[tf] = _frame(rows)
            observations = self.brain.observe(
                symbol=symbol, frames=frames,
                closed_bars=[x.to_bar() for x in candles["M5"]],
                as_of_utc=as_of_utc, actual_spread=actual_spread,
                broker_session_open=broker_session_open,
                data_fresh=data_fresh, news_blackout=news_blackout)
            plan = observations.proposal
            tool_context = _tools(candles["M5"], candles["M15"], frames["H1"].direction)
            risk = None
            if active_capital_native is not None:
                risk = AdaptiveRiskProfile().quote(
                    active_capital_native=active_capital_native,
                    account_currency=account_currency).fraction
            action = (plan.side.value if plan.ready_for_research
                      and news_context_verified else "WAIT")
            reasons = observations.regime.reasons + plan.evidence
            if not news_context_verified:
                reasons += ("news_context_unverified_no_trade",)
            decision_detail = self.advisor.decide(
                regime=observations.regime, proposal=plan, frames=frames,
                m5=candles["M5"], m15=candles["M15"],
                actual_spread=actual_spread,
                broker_session_open=broker_session_open,
                data_fresh=data_fresh,
                news_blackout=news_blackout,
                news_context_verified=news_context_verified,
            )
            # One public research signal: the explainable advisor may veto
            # an earlier direction-only candidate when scenario/entry checks
            # reveal poor geometry or mismatched playbook confirmation.
            action = decision_detail.signal
            entry_quality = None
            experimental_exit_plan = None
            semantic_setup = None
            if plan.side.value in ("BUY", "SELL") and plan.ready_for_research:
                semantic_setup = self.semantic_validator.assess(
                    side=plan.side.value, playbook=plan.strategy.value,
                    m5=candles["M5"], m15=candles["M15"], h1=candles["H1"],
                    spread=actual_spread, as_of_utc=as_of_utc,
                )
                entry_quality = self.entry_advisor.assess(
                    side=plan.side.value, playbook=plan.strategy.value,
                    m5=candles["M5"], m15=candles["M15"], h1=candles["H1"],
                    spread=actual_spread, as_of_utc=as_of_utc,
                )
                # Experimental SL/TP only: multi-pair retrospectives have NOT
                # established profitability; do not change the authoritative
                # research direction or live permission with this plan.
                if entry_quality.eligible and instrument_point is not None:
                    signal_close = candles["M5"][-1].close
                    shadow_entry = signal_close + (
                        actual_spread if plan.side.value == "BUY" else 0.0
                    )
                    experimental_exit_plan = self.exit_planner.plan(
                        side=plan.side.value, m5=candles["M5"],
                        m15=candles["M15"], h1=candles["H1"],
                        expected_entry=shadow_entry,
                        spread=actual_spread, point=instrument_point,
                        as_of_utc=as_of_utc,
                    )
                if use_semantic_setup_gate and not semantic_setup.pattern_confirmed:
                    action = "WAIT"
                    decision_detail = replace(
                        decision_detail, signal="WAIT", decision="WAIT",
                        entry_ready_for_research=False,
                        blockers=tuple(dict.fromkeys(
                            decision_detail.blockers +
                            ("playbook_semantics_not_confirmed",) +
                            semantic_setup.blockers)),
                        next_check=tuple(dict.fromkeys(
                            decision_detail.next_check + (semantic_setup.next_trigger,))),
                    )
                if use_structural_entry_gate and not entry_quality.eligible:
                    action = "WAIT"
                    decision_detail = replace(
                        decision_detail, signal="WAIT", decision="WAIT",
                        entry_ready_for_research=False,
                        blockers=tuple(dict.fromkeys(
                            decision_detail.blockers +
                            ("structural_entry_quality_rejected",) +
                            entry_quality.blockers)),
                        next_check=tuple(dict.fromkeys(
                            decision_detail.next_check + (entry_quality.next_trigger,))),
                    )
            return DecisionObservation(
                symbol, action, observations.regime.state.value,
                plan.strategy.value, reasons,
                tool_context, risk,
                potential_action=plan.side.value if plan.ready_for_research else "WAIT",
                setup_ready=bool(plan.ready_for_research),
                decision_detail=decision_detail,
                entry_quality=entry_quality,
                experimental_exit_plan=experimental_exit_plan,
                semantic_setup=semantic_setup)
        except (ValueError, KeyError, TypeError, ArithmeticError, OverflowError) as e:
            return self._wait(symbol, "sensor_or_risk_rejected:" + type(e).__name__)