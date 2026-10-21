from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from katarina.intelligence.perception.regime import Regime, RegimeAssessment


class EntryMode(str, Enum):
    TREND_PULLBACK = "TREND_PULLBACK"
    RANGE_MEAN_REVERSION = "RANGE_MEAN_REVERSION"
    MOMENTUM_BREAKOUT = "MOMENTUM_BREAKOUT"
    NONE = "NONE"


class EntrySide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class ScalperSnapshot:
    open: float
    high: float
    low: float
    close: float
    ema10: float
    ema50: float
    ema50_prev: float
    rsi14: float
    rsi2: float
    bb_lower: float
    bb_mid: float
    bb_upper: float
    atr14: float
    atr_avg50: float
    adx14: float
    reference_high: float
    reference_low: float
    vwap: float
    tick_velocity_norm: float
    orderflow_imbalance: float
    mtf_alignment: float
    htf_direction: int
    spread_bps: float
    session: str
    data_fresh: bool = True
    news_blackout: bool = False
    tradable_session: bool | None = None
    spread_limit_bps: float | None = None
    momentum_spread_limit_bps: float | None = None


@dataclass(frozen=True, slots=True)
class EntryProposal:
    valid: bool
    side: EntrySide
    mode: EntryMode
    score: float
    uncertainty: float
    expected_rr: float
    stop_atr_mult: float
    expiry_bars: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScalperEntryConfig:
    max_spread_bps: float = 3.0
    momentum_max_spread_bps: float = 4.0
    min_mtf_alignment: float = 0.55
    min_trend_adx: float = 20.0
    min_momentum_adx: float = 25.0
    trend_pullback_atr_tolerance: float = 0.25
    trend_min_ema50_slope_fraction: float = 0.00002
    trend_rr: float = 2.2
    trend_stop_atr_mult: float = 1.3
    range_stop_atr_mult: float = 1.2
    range_min_rr: float = 0.8
    range_max_adx: float = 24.0
    momentum_min_body_atr: float = 0.8
    momentum_min_velocity: float = 0.35
    momentum_min_imbalance: float = 0.15
    momentum_rr: float = 1.8
    momentum_stop_atr_mult: float = 1.0


class ScalperEntryEngine:
    """Deterministic multi-market entry router.

    It does not size positions, authorize live risk, or send broker orders.
    Market regime selects one setup family:
      TREND_* -> trend pullback
      RANGE -> RSI(2) + Bollinger mean reversion
      HIGH_VOL -> momentum breakout
      UNKNOWN -> NO TRADE
    """

    LIQUID_SESSIONS = {"LONDON", "NEW_YORK", "OVERLAP"}

    def __init__(self, config: ScalperEntryConfig | None = None):
        self.config = config or ScalperEntryConfig()

    @staticmethod
    def _none(*reasons: str) -> EntryProposal:
        return EntryProposal(
            False, EntrySide.NONE, EntryMode.NONE, 0.0, 1.0, 0.0, 0.0, 0, tuple(reasons)
        )

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def evaluate(self, regime: RegimeAssessment, s: ScalperSnapshot) -> EntryProposal:
        common = self._common_gate(s)
        if common is not None:
            return common
        if regime.out_of_distribution or regime.regime is Regime.UNKNOWN:
            return self._none("unknown_or_ood_regime")

        if regime.regime in {Regime.TREND_UP, Regime.TREND_DOWN}:
            return self._trend_pullback(regime, s)
        if regime.regime is Regime.RANGE:
            return self._range_mean_reversion(s)
        if regime.regime is Regime.HIGH_VOL:
            return self._momentum_breakout(s)
        return self._none("unsupported_regime")

    def _common_gate(self, s: ScalperSnapshot) -> EntryProposal | None:
        numeric = (
            s.open, s.high, s.low, s.close, s.ema10, s.ema50, s.ema50_prev,
            s.bb_lower, s.bb_mid, s.bb_upper, s.atr14, s.atr_avg50,
            s.reference_high, s.reference_low, s.vwap,
        )
        if not s.data_fresh:
            return self._none("stale_data")
        if s.news_blackout:
            return self._none("high_impact_news_blackout")
        if s.tradable_session is False:
            return self._none("outside_tradable_session")
        if s.tradable_session is None and s.session.upper() not in self.LIQUID_SESSIONS:
            return self._none("outside_liquid_session")
        if any(v <= 0 for v in numeric):
            return self._none("invalid_market_inputs")
        if not (0.0 <= s.mtf_alignment <= 1.0):
            return self._none("invalid_mtf_alignment")
        if s.htf_direction not in {-1, 0, 1}:
            return self._none("invalid_htf_direction")
        if s.spread_bps < 0:
            return self._none("invalid_spread")
        return None

    def _trend_pullback(self, regime: RegimeAssessment, s: ScalperSnapshot) -> EntryProposal:
        c = self.config
        spread_limit=c.max_spread_bps if s.spread_limit_bps is None else s.spread_limit_bps
        if s.spread_bps > spread_limit:
            return self._none("spread_too_wide")
        if s.adx14 < c.min_trend_adx:
            return self._none("trend_adx_too_low")
        if s.mtf_alignment < c.min_mtf_alignment:
            return self._none("mtf_alignment_too_low")
        if s.atr_avg50 <= 0 or s.atr14 < 0.80 * s.atr_avg50:
            return self._none("inactive_volatility")

        is_buy = regime.regime is Regime.TREND_UP
        side = EntrySide.BUY if is_buy else EntrySide.SELL
        desired = 1 if is_buy else -1
        if s.htf_direction not in {0, desired}:
            return self._none("htf_bias_conflict")

        slope_fraction = (s.ema50 - s.ema50_prev) / max(abs(s.ema50_prev), 1e-12)
        if desired * slope_fraction < c.trend_min_ema50_slope_fraction:
            return self._none("ema50_slope_not_confirmed")

        distance_to_ema = abs(s.close - s.ema10) / s.atr14
        touched = s.low <= s.ema10 + c.trend_pullback_atr_tolerance * s.atr14 if is_buy else s.high >= s.ema10 - c.trend_pullback_atr_tolerance * s.atr14
        bounce = s.close > s.open and s.close >= s.ema10 if is_buy else s.close < s.open and s.close <= s.ema10
        if not touched or not bounce or distance_to_ema > 0.65:
            return self._none("pullback_bounce_not_confirmed")

        if is_buy and not (45.0 <= s.rsi14 <= 65.0):
            return self._none("rsi_not_in_long_sweet_spot")
        if not is_buy and not (35.0 <= s.rsi14 <= 55.0):
            return self._none("rsi_not_in_short_sweet_spot")

        alignment_bonus = 0.16 * s.mtf_alignment
        adx_bonus = 0.10 * self._clip01((s.adx14 - c.min_trend_adx) / 20.0)
        pullback_bonus = 0.10 * self._clip01(1.0 - distance_to_ema / 0.65)
        score = min(0.95, 0.56 + alignment_bonus + adx_bonus + pullback_bonus)
        return EntryProposal(
            True, side, EntryMode.TREND_PULLBACK, score, 1.0 - score,
            c.trend_rr, c.trend_stop_atr_mult, 3,
            ("regime_trend", "ema50_slope", "ema10_pullback_bounce", "rsi_sweet_spot", "active_atr", "mtf_aligned"),
        )

    def _range_mean_reversion(self, s: ScalperSnapshot) -> EntryProposal:
        c = self.config
        spread_limit=c.max_spread_bps if s.spread_limit_bps is None else s.spread_limit_bps
        if s.spread_bps > spread_limit:
            return self._none("spread_too_wide")
        if s.adx14 > c.range_max_adx:
            return self._none("range_adx_too_high")
        if s.mtf_alignment > 0.70:
            return self._none("range_conflicts_with_strong_mtf_trend")

        is_buy = s.rsi2 < 10.0 and s.close <= s.bb_lower
        is_sell = s.rsi2 > 90.0 and s.close >= s.bb_upper
        if not is_buy and not is_sell:
            return self._none("rsi2_bb_extreme_not_present")

        side = EntrySide.BUY if is_buy else EntrySide.SELL
        target_distance = abs(s.bb_mid - s.close)
        expected_rr = target_distance / (s.atr14 * c.range_stop_atr_mult)
        if expected_rr < c.range_min_rr:
            return self._none("mean_reversion_reward_too_small")

        extreme = (10.0 - s.rsi2) / 10.0 if is_buy else (s.rsi2 - 90.0) / 10.0
        band_extension = (s.bb_lower - s.close) / s.atr14 if is_buy else (s.close - s.bb_upper) / s.atr14
        score = min(
            0.94,
            0.60
            + 0.12 * self._clip01(extreme)
            + 0.10 * self._clip01(band_extension)
            + 0.08 * self._clip01((c.range_max_adx - s.adx14) / c.range_max_adx)
        )
        return EntryProposal(
            True, side, EntryMode.RANGE_MEAN_REVERSION, score, 1.0 - score,
            expected_rr, c.range_stop_atr_mult, 15,
            ("range_regime", "rsi2_extreme", "bollinger_outer_touch", "bb_mid_target", "liquid_session"),
        )

    def _momentum_breakout(self, s: ScalperSnapshot) -> EntryProposal:
        c = self.config
        spread_limit=c.momentum_max_spread_bps if s.momentum_spread_limit_bps is None else s.momentum_spread_limit_bps
        if s.spread_bps > spread_limit:
            return self._none("spread_too_wide_for_momentum")
        if s.adx14 < c.min_momentum_adx:
            return self._none("momentum_adx_too_low")

        body_atr = abs(s.close - s.open) / s.atr14
        if body_atr < c.momentum_min_body_atr:
            return self._none("bar_body_not_expansive")

        buy_break = s.close > s.reference_high
        sell_break = s.close < s.reference_low
        if not buy_break and not sell_break:
            return self._none("reference_level_not_broken")

        side = EntrySide.BUY if buy_break else EntrySide.SELL
        sign = 1.0 if buy_break else -1.0
        if sign * s.tick_velocity_norm < c.momentum_min_velocity:
            return self._none("tick_velocity_not_confirmed")
        if sign * s.orderflow_imbalance < c.momentum_min_imbalance:
            return self._none("orderflow_not_confirmed")
        if s.htf_direction == -int(sign) and s.mtf_alignment >= 0.65:
            return self._none("strong_htf_conflict")

        vwap_ok = s.close >= s.vwap if buy_break else s.close <= s.vwap
        if not vwap_ok:
            return self._none("vwap_context_conflict")

        score = min(
            0.97,
            0.57
            + 0.12 * self._clip01((body_atr - c.momentum_min_body_atr) / 1.2)
            + 0.10 * self._clip01((s.adx14 - c.min_momentum_adx) / 25.0)
            + 0.09 * self._clip01(abs(s.tick_velocity_norm))
            + 0.09 * self._clip01(abs(s.orderflow_imbalance))
        )
        return EntryProposal(
            True, side, EntryMode.MOMENTUM_BREAKOUT, score, 1.0 - score,
            c.momentum_rr, c.momentum_stop_atr_mult, 2,
            ("high_vol_regime", "reference_breakout", "expansion_bar", "adx_confirmed", "tick_velocity", "orderflow", "vwap_confirmed"),
        )
