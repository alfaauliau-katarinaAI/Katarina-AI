"""Explainable, adaptive and read-only market decision advisor.

Closed-candle context -> hypothesis -> suitable playbook -> explicit entry/WAIT reasons.
Scores express corroborating EVIDENCE, not win probability. No order or live-risk path.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence

from katarina.intelligence.adaptive_regime import (
    ClosedFrame, MarketRead, MarketState, Playbook,
)
from katarina.engines.adaptive_scalper import ResearchEntryPlan


@dataclass(frozen=True)
class MarketScenario:
    direction: str
    premise: str
    reference_price: float | None
    target: float | None
    invalidation: float | None
    confirmation: str
    # Geometric price-distance ratio, NOT an estimate of actual return.
    indicative_rr: float | None


@dataclass(frozen=True)
class StrategyAssessment:
    playbook: str
    evidence_score: float
    rationale: tuple[str, ...]
    # Whether the existing closed-candle router can support this playbook now.
    price_confirmed: bool


@dataclass(frozen=True)
class MarketDecision:
    """Complete six-question narrative, without authorizing a broker order."""

    activity: str
    direction: str
    evidence_strength: float
    primary: MarketScenario
    alternative: MarketScenario
    selected_strategy: str
    ranked_strategies: tuple[StrategyAssessment, ...]
    signal: str
    decision: str
    entry_ready_for_research: bool
    blockers: tuple[str, ...]
    explanations: tuple[str, ...]
    explanations_id: tuple[str, ...]
    next_check: tuple[str, ...]
    support: float
    resistance: float
    snapshot_utc: str
    evidence_score_is_probability: bool = False
    research_only: bool = True
    live_execution_authorized: bool = False


# The mapping is a prior, not a command to trade or a claim of historical edge.
_PRIORS: dict[Playbook, dict[MarketState, float]] = {
    Playbook.TREND_PULLBACK: {
        MarketState.TREND_UP: .56, MarketState.TREND_DOWN: .56,
        MarketState.PULLBACK_UP: .68, MarketState.PULLBACK_DOWN: .68,
        MarketState.BREAKOUT_UP: .18, MarketState.BREAKOUT_DOWN: .18,
    },
    Playbook.RANGE_FADE: {MarketState.SIDEWAYS: .72},
    Playbook.BREAKOUT_RETEST: {
        MarketState.BREAKOUT_UP: .72, MarketState.BREAKOUT_DOWN: .72,
        MarketState.TREND_UP: .20, MarketState.TREND_DOWN: .20,
    },
    Playbook.REVERSAL_RECLAIM: {
        MarketState.REVERSAL_UP: .75, MarketState.REVERSAL_DOWN: .75,
    },
    Playbook.MOMENTUM_CONTINUATION: {
        MarketState.TREND_UP: .38, MarketState.TREND_DOWN: .38,
        MarketState.BREAKOUT_UP: .48, MarketState.BREAKOUT_DOWN: .48,
    },
}
_UNCERTAIN = {
    MarketState.UNKNOWN, MarketState.TRANSITION, MarketState.VOLATILITY_SHOCK,
}


def _scenario(side: int, price: float, low: float, high: float, atr: float,
              playbook: str, *, alternate: bool = False) -> MarketScenario:
    if side == 0 or not (low < high and atr > 0):
        return MarketScenario(
            "NEUTRAL", "Belum ada skenario arah yang layak diklaim.",
            price, None, None,
            "Tunggu penutupan harga di luar batas range atau struktur baru.", None,
        )
    direction = "BULLISH" if side > 0 else "BEARISH"
    # The 20-bar channel is descriptive; forecasts are explicitly conditional.
    if side > 0:
        target = high if high > price else price + 1.5 * atr
        invalidation = max(low, price - atr)
        confirmation = "Tunggu close bullish dan retest/penolakan support terverifikasi."
    else:
        target = low if low < price else price - 1.5 * atr
        invalidation = min(high, price + atr)
        confirmation = "Tunggu close bearish dan retest/penolakan resistance terverifikasi."
    distance = side * (price - invalidation)
    reward = side * (target - price)
    ratio = round(reward / distance, 3) if distance > 0 and reward > 0 else None
    premise = ("Skenario alternatif jika struktur arah utama gagal: "
               if alternate else "Hipotesis bersyarat dari struktur dan harga tertutup: ")
    premise += ("kelanjutan naik menuju area resistance/ekspansi."
                if side > 0 else "kelanjutan turun menuju area support/ekspansi.")
    return MarketScenario(direction, premise, round(price, 8), round(target, 8),
                          round(invalidation, 8), confirmation, ratio)


class AdaptiveMarketDecisionAdvisor:
    """Flexible evidence-weighted *research* routing; hard risk gates stay hard."""

    def decide(
        self, *, regime: MarketRead, proposal: ResearchEntryPlan,
        frames: Mapping[str, ClosedFrame], m5: Sequence[object],
        m15: Sequence[object], actual_spread: float,
        broker_session_open: bool, data_fresh: bool,
        news_blackout: bool, news_context_verified: bool,
    ) -> MarketDecision:
        if len(m5) < 21 or len(m15) < 21:
            raise ValueError("insufficient_closed_candles")
        if not isfinite(actual_spread) or actual_spread < 0:
            raise ValueError("invalid_spread")

        price = float(m5[-1].close)
        low = min(float(b.low) for b in m15[-21:-1])
        high = max(float(b.high) for b in m15[-21:-1])
        atr = float(frames["M15"].atr)
        side = regime.directional_bias
        status = regime.state
        if status in _UNCERTAIN:
            side = 0

        # Explicit descriptions, not forecasts of certain price movement.
        activity = {
            MarketState.TREND_UP: "TRENDING",
            MarketState.TREND_DOWN: "TRENDING",
            MarketState.PULLBACK_UP: "PULLBACK",
            MarketState.PULLBACK_DOWN: "PULLBACK",
            MarketState.SIDEWAYS: "SIDEWAYS",
            MarketState.BREAKOUT_UP: "BREAKOUT",
            MarketState.BREAKOUT_DOWN: "BREAKOUT",
            MarketState.REVERSAL_UP: "REVERSAL_UNDER_CONFIRMATION",
            MarketState.REVERSAL_DOWN: "REVERSAL_UNDER_CONFIRMATION",
            MarketState.VOLATILITY_SHOCK: "VOLATILITY_SHOCK",
            MarketState.TRANSITION: "NO_CONCLUSION",
            MarketState.UNKNOWN: "UNKNOWN",
        }[status]
        direction = ("BULLISH" if side > 0 else "BEARISH" if side < 0 else
                     "SIDEWAYS" if status == MarketState.SIDEWAYS else "UNCERTAIN")

        # Position and candle patterns complement the regime, they do not
        # become independent proof of returns.
        bar = m5[-1]
        body = abs(float(bar.close) - float(bar.open))
        candle_range = max(float(bar.high) - float(bar.low), 1e-12)
        body_ratio = body / candle_range
        bull_candle = bar.close > bar.open
        bear_candle = bar.close < bar.open
        near_support = price <= low + .30 * (high - low)
        near_resistance = price >= high - .30 * (high - low)
        channel_break_up = price > high
        channel_break_down = price < low
        mtf_direction = (frames["M15"].direction, frames["H1"].direction)
        agreement = (sum(x == side for x in mtf_direction) / 2
                     if side else 0.0)
        high_body = body_ratio >= .55
        direction_candle = ((side > 0 and bull_candle) or
                            (side < 0 and bear_candle))
        scores = []
        if side != 0 or status == MarketState.SIDEWAYS:
            for playbook, table in _PRIORS.items():
                base = table.get(status, 0.0)
                if base <= 0:
                    continue
                evidence = []
                score = base + min(.09, .12 * regime.evidence_strength)
                if side and agreement:
                    score += .08 * agreement
                    evidence.append("higher_timeframe_support")
                if side and direction_candle:
                    score += .045
                    evidence.append("closed_candle_direction")
                if direction_candle and high_body:
                    score += .025
                    evidence.append("meaningful_candle_body")
                if playbook == Playbook.RANGE_FADE and (near_support or near_resistance):
                    score += .08
                    evidence.append("range_boundary_location")
                if playbook in (Playbook.BREAKOUT_RETEST,
                                Playbook.MOMENTUM_CONTINUATION) and (
                                    (side > 0 and channel_break_up) or
                                    (side < 0 and channel_break_down)):
                    score += .10
                    evidence.append("closed_channel_break")
                if playbook == regime.playbook:
                    evidence.append("regime_playbook_alignment")
                scores.append(StrategyAssessment(
                    playbook.value, round(min(1.0, score), 4),
                    tuple(evidence) or ("regime_context_only",),
                    proposal.ready_for_research
                    and playbook == proposal.strategy,
                ))
        scores.sort(key=lambda x: (-x.evidence_score, x.playbook))
        selected = (scores[0].playbook if scores and
                    scores[0].evidence_score >= .42 else "OBSERVE")
        # Never interpret scenario price levels as executable stops or targets.
        if status == MarketState.SIDEWAYS:
            if near_support:
                invalidation = low - .15 * atr
                reward, risk = high - price, price - invalidation
                rr = round(reward / risk, 3) if reward > 0 and risk > 0 else None
                first = MarketScenario(
                    "BULLISH_WITHIN_RANGE",
                    "Jika support bertahan, harga berpotensi menguji resistance range.",
                    round(price, 8), round(high, 8), round(invalidation, 8),
                    "Tunggu candle penolakan bullish dekat support, bukan buy buta.",
                    rr)
            elif near_resistance:
                invalidation = high + .15 * atr
                reward, risk = price - low, invalidation - price
                rr = round(reward / risk, 3) if reward > 0 and risk > 0 else None
                first = MarketScenario(
                    "BEARISH_WITHIN_RANGE",
                    "Jika resistance bertahan, harga berpotensi turun ke support range.",
                    round(price, 8), round(low, 8), round(invalidation, 8),
                    "Tunggu candle penolakan bearish dekat resistance, bukan sell buta.",
                    rr)
            else:
                first = MarketScenario(
                    "SIDEWAYS", "Harga di tengah range: arah berikutnya belum unggul.",
                    round(price, 8), None, None,
                    "Tunggu harga mendekati support/resistance atau breakout terkonfirmasi.",
                    None)
            alternate = MarketScenario(
                "UNCERTAIN", "Breakout dapat mengakhiri range.",
                round(price, 8), None, None,
                "Tunggu close breakout, lalu validasi apakah harga bertahan.", None)
        else:
            first = _scenario(side, price, low, high, atr, selected)
            alternate = _scenario(-side, price, low, high, atr,
                                  "ALTERNATIVE", alternate=True)
        blockers = []
        if status in _UNCERTAIN:
            blockers.append("market_structure_not_resolved")
        if not broker_session_open:
            blockers.append("broker_session_closed")
        if not data_fresh:
            blockers.append("stale_market_data")
        if news_blackout:
            blockers.append("high_impact_news_blackout")
        if not news_context_verified:
            blockers.append("news_context_not_verified")
        # Retain authoritative router confirmation; flexibility is for
        # strategy ranking, not inventing unconfirmed BUY or SELL triggers.
        if not proposal.ready_for_research:
            blockers.append("entry_price_action_not_confirmed")
        if selected == "OBSERVE":
            blockers.append("no_matching_playbook")
        if selected != "OBSERVE" and selected != proposal.strategy.value:
            blockers.append("selected_playbook_needs_own_entry_confirmation")
        spread_atr = actual_spread / max(atr, 1e-12)
        if spread_atr > .42:
            blockers.append("spread_excessive_relative_to_atr")
        if first.indicative_rr is not None and first.indicative_rr < 1:
            blockers.append("scenario_reward_distance_too_small")
        if side == 0 and status != MarketState.SIDEWAYS:
            blockers.append("direction_uncertain")
        # An apparently valid price signal is a PAPER hypothesis, not an
        # approved trading strategy. No configuration was validated OOS.
        paper_ready = not blockers and selected != "OBSERVE"
        if paper_ready:
            decision = "RESEARCH_SETUP"
            signal = proposal.side.value
        else:
            decision = "WAIT"
            signal = "WAIT"
        evidence = list(regime.reasons)
        evidence.extend(scores[0].rationale if scores else ("insufficient_structure",))
        evidence.extend(proposal.evidence)
        translations = {
            "aligned_h1_m15": "H1 dan M15 menunjukkan arah yang selaras.",
            "directional_continuation": "Pergerakan tertutup mendukung kelanjutan tren.",
            "opposing_m5_pullback": "M5 sedang melawan arah tren timeframe besar: fase pullback.",
            "multi_frame_low_directional_efficiency": "Beberapa timeframe bergerak tidak efisien: indikasi sideways.",
            "conflicting_mtf_without_structure": "Arah antar-timeframe masih bertentangan tanpa konfirmasi struktur.",
            "verified_swing_reclaim": "Swing penting telah direbut kembali melalui penutupan harga.",
            "closed_swing_break": "Ada penutupan harga melewati swing sebelumnya.",
            "range_expansion": "Range mulai melebar; breakout masih perlu dikonfirmasi.",
            "rejection": "Ada candle penolakan pada area struktural.",
            "higher_timeframe_opposed": "Timeframe lebih besar masih melawan sinyal reversal.",
            "higher_timeframe_support": "Arah H1/M15 mendukung skenario.",
            "closed_candle_direction": "Candle yang sudah tutup mengikuti bias pasar.",
            "meaningful_candle_body": "Badan candle relatif kuat terhadap rentangnya.",
            "range_boundary_location": "Harga berada dekat batas range sebelumnya.",
            "closed_channel_break": "Close sudah melewati batas channel sebelumnya.",
            "regime_playbook_alignment": "Strategi cocok dengan fase pasar.",
            "regime_context_only": "Kecocokan strategi masih berdasarkan regime saja.",
            "trend_pullback_or_continuation": "Ada indikasi pullback/kelanjutan arah utama.",
            "closed_bar_price_action": "Pembacaan memakai harga candle tertutup.",
            "range_edge_rejection": "Area tepi range menunjukkan reaksi harga.",
            "confirmed_structural_breakout": "Struktur breakout telah menutup di luar batas.",
            "structure_reclaim_direction_confirmed": "Reclaim struktur mendukung arah reversal.",
            "insufficient_structure": "Struktur yang tersedia belum memadai untuk kesimpulan.",
        }
        explanations_id = tuple(dict.fromkeys(
            translations.get(reason, "Bukti teknis: " + reason.replace("_", " "))
            for reason in evidence
        ))
        checks = {
            "market_structure_not_resolved": "Tunggu H1/M15 selaras atau bukti struktur baru.",
            "broker_session_closed": "Evaluasi ulang setelah sesi broker dibuka.",
            "stale_market_data": "Sinkronkan quote dan candle tertutup terbaru.",
            "high_impact_news_blackout": "Tunggu periode blackout berita berakhir.",
            "news_context_not_verified": "Verifikasi konteks berita sebelum entry.",
            "entry_price_action_not_confirmed": "Tunggu konfirmasi candle/level pada playbook.",
            "selected_playbook_needs_own_entry_confirmation":
                "Tunggu sinyal khusus untuk playbook alternatif yang terpilih.",
            "no_matching_playbook": "Tetap observasi sampai regime mendapat playbook.",
            "spread_excessive_relative_to_atr": "Tunggu spread kembali wajar.",
            "scenario_reward_distance_too_small": "Tunggu lokasi harga yang memberi ruang target cukup.",
            "direction_uncertain": "Tunggu konflik timeframe dan struktur harga selesai.",
        }
        next_check = tuple(dict.fromkeys(checks[b] for b in blockers))
        if not blockers:
            next_check = (
                "Validasi statistik, biaya, risk governor, dan forward demo "
                "sebelum mempertimbangkan order nyata.",
            )
        return MarketDecision(
            activity=activity, direction=direction,
            evidence_strength=round(regime.evidence_strength, 4),
            primary=first, alternative=alternate,
            selected_strategy=selected,
            ranked_strategies=tuple(scores),
            signal=signal, decision=decision,
            entry_ready_for_research=paper_ready,
            blockers=tuple(dict.fromkeys(blockers)),
            explanations=tuple(dict.fromkeys(evidence)),
            explanations_id=explanations_id,
            next_check=next_check,
            support=round(low, 8), resistance=round(high, 8),
            snapshot_utc=m5[-1].closed_at_utc.isoformat(),
        )