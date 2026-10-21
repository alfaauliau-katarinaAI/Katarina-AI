"""Evolutionary discovery of causal trading RULE COMBINATIONS (research-only).

Searches conjunctions of price-derived features, sides, exits and holding
horizons. No LLM necessary; no broker connection or order interface.
Caution: simulated OHLC fills, not independently verified trading profit.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite, log, sqrt
from random import Random
from statistics import mean, stdev

FEATURE_LEVELS = {
    "momentum_3": (-1.5, -0.5, 0.5, 1.5),
    "momentum_8": (-2.0, -0.7, 0.7, 2.0),
    "range_location": (0.2, 0.4, 0.6, 0.8),
    "candle_body": (-0.6, -0.2, 0.2, 0.6),
    "wick_bias": (-0.5, -0.15, 0.15, 0.5),
    "volatility_ratio": (0.7, 0.9, 1.1, 1.5),
    "breakout_8": (-0.8, -0.2, 0.2, 0.8),
}
SIDE_OPTIONS = ("BUY", "SELL")
HORIZONS = (3, 6, 10)
STOPS = (1.0, 1.5, 2.0)
REWARDS = (1.0, 1.5, 2.0)
MIN_BARS = 720
MAX_BARS = 12000
MAX_TRIALS = 192
MIN_GROUP_TRADES = 8
MIN_GROUP_DAYS = 4


@dataclass(frozen=True, slots=True)
class Candle:
    """OHLC are bar-mid approximations, close_at is UTC candle close."""
    close_at: int
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self):
        if not isinstance(self.close_at, int) or self.close_at <= 0:
            raise ValueError("invalid_bar_close_time")
        vals = (self.open, self.high, self.low, self.close)
        if any(not isfinite(v) or v <= 0 for v in vals):
            raise ValueError("invalid_bar_prices")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("invalid_ohlc_geometry")


@dataclass(frozen=True, slots=True)
class Rule:
    feature: str
    op: str
    level: float

    def __post_init__(self):
        if (self.feature not in FEATURE_LEVELS or
                self.level not in FEATURE_LEVELS[self.feature] or
                self.op not in (">=", "<=")):
            raise ValueError("unsafe_rule")


@dataclass(frozen=True, slots=True)
class Genome:
    side: str
    conditions: tuple[Rule, ...]
    stop_atr: float
    reward_r: float
    horizon_bars: int

    def __post_init__(self):
        if (self.side not in SIDE_OPTIONS or
                not 1 <= len(self.conditions) <= 3 or
                len({r.feature for r in self.conditions}) != len(self.conditions) or
                self.stop_atr not in STOPS or self.reward_r not in REWARDS or
                self.horizon_bars not in HORIZONS):
            raise ValueError("unsafe_genome")

    def to_dict(self) -> dict:
        return {
            "side": self.side,
            "conditions": [{"feature": r.feature, "op": r.op, "level": r.level}
                           for r in self.conditions],
            "stop_atr": self.stop_atr,
            "reward_r": self.reward_r,
            "horizon_bars": self.horizon_bars,
        }

    @property
    def fingerprint(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode()).hexdigest()[:20]


def validate_bars(bars: tuple[Candle, ...]) -> None:
    if not MIN_BARS <= len(bars) <= MAX_BARS:
        raise ValueError("insufficient_or_excessive_closed_bars")
    if any(not isinstance(x, Candle) for x in bars):
        raise ValueError("candle_type_required")
    if any(bars[i].close_at >= bars[i+1].close_at for i in range(len(bars)-1)):
        raise ValueError("noncausal_duplicate_or_reversed_bars")
    # No timestamp gap interpolation is fabricated; suspicious data remain
    # visible and this is explicitly not a broker-grade tick replay.


def _features(bars: tuple[Candle, ...]) -> list[dict]:
    features: list[dict] = [{} for _ in bars]
    tr = []
    for i, b in enumerate(bars):
        prev = bars[i-1].close if i else b.close
        tr.append(max(b.high-b.low, abs(b.high-prev), abs(b.low-prev)))
        if i < 24:
            continue
        atr = mean(tr[i-13:i+1])
        if atr <= 0:
            continue
        recent = bars[i-7:i+1]
        ceiling = max(x.high for x in recent)
        floor = min(x.low for x in recent)
        candle_range = max(b.high-b.low, 1e-12)
        features[i] = {
            "atr": atr,
            "momentum_3": (b.close-bars[i-3].close)/atr,
            "momentum_8": (b.close-bars[i-8].close)/atr,
            "range_location": (b.close-floor)/max(ceiling-floor, 1e-12),
            "candle_body": (b.close-b.open)/candle_range,
            "wick_bias": ((min(b.open,b.close)-b.low) -
                          (b.high-max(b.open,b.close)))/candle_range,
            "volatility_ratio": mean(tr[i-3:i+1])/max(mean(tr[i-13:i+1]),1e-12),
            # The previous eight bars are known before the current close.
            "breakout_8": ((b.close-max(x.high for x in bars[i-8:i]))/atr
                           if b.close >= bars[i-1].close else
                           (b.close-min(x.low for x in bars[i-8:i]))/atr),
        }
    return features


def _matches(genome: Genome, row: dict) -> bool:
    if not row:
        return False
    return all(row[c.feature] >= c.level if c.op == ">="
               else row[c.feature] <= c.level for c in genome.conditions)


def _simulate(bars: tuple[Candle, ...], i: int, genome: Genome, atr: float,
              *, spread_fraction: float, fee_r: float) -> tuple[int, float]:
    """Enter NEXT bar at half-spread. Stop wins on ambiguous OHLC bar."""
    entry_idx = i+1
    entry_mid = bars[entry_idx].open
    spread = atr*spread_fraction
    direction = 1 if genome.side == "BUY" else -1
    entry = entry_mid+direction*spread/2
    risk = atr*genome.stop_atr
    stop = entry-direction*risk
    target = entry+direction*risk*genome.reward_r
    last = min(entry_idx+genome.horizon_bars-1, len(bars)-1)
    for j in range(entry_idx,last+1):
        b = bars[j]
        low = b.low-direction*spread/2
        high = b.high-direction*spread/2
        opened = b.open-direction*spread/2
        if direction == 1:
            stop_hit = low <= stop
            target_hit = high >= target
            stop_fill = min(stop,opened) if opened <= stop else stop
        else:
            stop_hit = high >= stop
            target_hit = low <= target
            stop_fill = max(stop,opened) if opened >= stop else stop
        if stop_hit:  # both hit => loss, never guess the intrabar sequence
            price = stop_fill
        elif target_hit:
            price = target  # favorable gaps receive no extra reward
        else:
            continue
        return j, round(direction*(price-entry)/risk-fee_r, 6)
    close = bars[last].close-direction*spread/2
    return last, round(direction*(close-entry)/risk-fee_r, 6)


def _outcomes(bars: tuple[Candle, ...], features: list[dict], genome: Genome,
              start: int, end: int, *, spread_fraction: float,
              fee_r: float) -> list[tuple[int, float]]:
    """No position crosses a split; one trade at a time per candidate."""
    rows = []
    i = max(24, start)
    while i < end-1:
        f = features[i]
        if not _matches(genome,f):
            i += 1
            continue
        exit_idx, outcome = _simulate(bars,i,genome,f["atr"],
                                      spread_fraction=spread_fraction,fee_r=fee_r)
        if exit_idx >= end:
            break  # never use a label from another segment
        rows.append((bars[i+1].close_at,outcome))
        i = exit_idx+1
    return rows


def _measure(trades: list[tuple[int,float]]) -> dict:
    vals = [x for _,x in trades]
    gains = sum(v for v in vals if v > 0)
    losses = -sum(v for v in vals if v < 0)
    days = len({datetime.fromtimestamp(t,timezone.utc).date() for t,_ in trades})
    return {
        "trades": len(vals), "utc_days": days,
        "mean_modelled_r": round(mean(vals),6) if vals else None,
        "profit_factor": round(gains/losses,6) if losses else None,
        "worst_modelled_r": round(min(vals),6) if vals else None,
    }


def _random_rule(rng: Random, excluded=()) -> Rule:
    features = sorted(set(FEATURE_LEVELS)-set(excluded))
    feat = rng.choice(features)
    return Rule(feat,rng.choice((">=","<=")),rng.choice(FEATURE_LEVELS[feat]))


def _new_genome(rng: Random) -> Genome:
    count = rng.choice((1,2,2,3))
    rules = []
    for _ in range(count):
        rules.append(_random_rule(rng,[r.feature for r in rules]))
    return Genome(rng.choice(SIDE_OPTIONS),tuple(rules),rng.choice(STOPS),
                  rng.choice(REWARDS),rng.choice(HORIZONS))


def _mutate(g: Genome, rng: Random) -> Genome:
    side, rules, stop, reward, horizon = (
        g.side,list(g.conditions),g.stop_atr,g.reward_r,g.horizon_bars)
    choice = rng.randrange(6)
    if choice == 0:
        side = "BUY" if side == "SELL" else "SELL"
    elif choice == 1:
        n = rng.randrange(len(rules))
        rules[n] = Rule(rules[n].feature,
                        "<=" if rules[n].op == ">=" else ">=",
                        rng.choice(FEATURE_LEVELS[rules[n].feature]))
    elif choice == 2:
        n = rng.randrange(len(rules))
        rules[n] = _random_rule(rng,[r.feature for i,r in enumerate(rules) if i != n])
    elif choice == 3:
        if len(rules) < 3 and rng.random() < .5:
            rules.append(_random_rule(rng,[r.feature for r in rules]))
        elif len(rules) > 1:
            del rules[rng.randrange(len(rules))]
        else:
            rules[0] = _random_rule(rng)
    elif choice == 4:
        stop = rng.choice(STOPS)
        reward = rng.choice(REWARDS)
    else:
        horizon = rng.choice(HORIZONS)
    return Genome(side,tuple(rules),stop,reward,horizon)


def discover(bars: tuple[Candle, ...], *, seed: int = 42,
             population: int = 20, generations: int = 4,
             spread_atr: float = .04, fee_r: float = .04) -> dict:
    """Bounded evolutionary search with immutable final chronological holdout.

    Fitness sees train+validation only. Holdout is evaluated for at most 3
    fixed shortlisted variants and NEVER influences mutation/selection.
    """
    validate_bars(bars)
    if (not isinstance(seed,int) or not 8 <= population <= 24 or
            not 1 <= generations <= 8 or
            population*generations > MAX_TRIALS or
            not all(isfinite(x) for x in (spread_atr,fee_r)) or
            not 0 <= spread_atr <= .30 or not 0 <= fee_r <= .30):
        raise ValueError("invalid_bounded_discovery_settings")
    n = len(bars)
    train_end = int(n*.60)
    validation_end = int(n*.80)
    feats = _features(bars)
    rng = Random(seed)
    pool = [_new_genome(rng) for _ in range(population)]
    evaluated: dict[str,tuple[float,Genome,dict,dict]] = {}
    for generation in range(generations):
        for genome in pool:
            if genome.fingerprint in evaluated:
                continue
            tr = _outcomes(bars,feats,genome,24,train_end,
                           spread_fraction=spread_atr,fee_r=fee_r)
            va = _outcomes(bars,feats,genome,train_end,validation_end,
                           spread_fraction=spread_atr,fee_r=fee_r)
            train, val = _measure(tr),_measure(va)
            fitness = -1e6
            if (train["trades"] >= MIN_GROUP_TRADES and
                    val["trades"] >= MIN_GROUP_TRADES and
                    train["utc_days"] >= MIN_GROUP_DAYS and
                    val["utc_days"] >= MIN_GROUP_DAYS):
                vals=[x for _,x in va]
                sigma=stdev(vals) if len(vals)>1 else 1.
                # Penalizes sampling error and unsearched curve complexity.
                fitness=(mean(vals)-1.96*sigma/sqrt(len(vals))
                         -.025*len(genome.conditions))
            evaluated[genome.fingerprint]=(fitness,genome,train,val)
        leaders=sorted(evaluated.values(),key=lambda x:(-x[0],x[1].fingerprint))
        parents=[x[1] for x in leaders[:min(6,len(leaders))]]
        pool=parents[:]
        while len(pool)<population:
            pool.append(_mutate(rng.choice(parents),rng)
                        if rng.random()<.8 else _new_genome(rng))
    eligible=sorted((v for v in evaluated.values() if v[0]>-1e5),
                    key=lambda x:(-x[0],x[1].fingerprint))
    # Number of attempts is reported; more tests require stronger evidence.
    attempts=len(evaluated)
    results=[]
    for fitness,genome,train,val in eligible[:3]:
        hold=_measure(_outcomes(bars,feats,genome,validation_end,n,
                                spread_fraction=spread_atr,fee_r=fee_r))
        multiple_test_haircut=.06*sqrt(log(attempts+1))
        robust=(val["mean_modelled_r"] is not None and
                hold["mean_modelled_r"] is not None and
                val["trades"]>=MIN_GROUP_TRADES and
                hold["trades"]>=MIN_GROUP_TRADES and
                hold["utc_days"]>=MIN_GROUP_DAYS and
                fitness-multiple_test_haircut>0 and
                hold["mean_modelled_r"]>0)
        results.append({
            "candidate_id":genome.fingerprint,
            "genome":genome.to_dict(),
            "train":train,"validation":val,"held_out":hold,
            "search_fitness_after_penalties":round(fitness-multiple_test_haircut,6),
            "research_status":("FURTHER_PROSPECTIVE_VALIDATION_REQUIRED"
                               if robust else "UNSTABLE_OR_INSUFFICIENT_EVIDENCE"),
            "can_authorize_live":False,
        })
    original=[(b.close_at,b.open,b.high,b.low,b.close) for b in bars]
    return {
        "engine":"KATARINA_EVOLUTIONARY_RULE_DISCOVERY_V1",
        "algorithm":"BOUNDED_CAUSAL_GENETIC_SEARCH",
        "data_sha256":sha256(json.dumps(original,separators=(",",":")).encode()).hexdigest(),
        "bars":n,"seed":seed,
        "training_end_index":train_end,
        "validation_end_index":validation_end,
        "holdout_start_index":validation_end,
        "candidate_trials":attempts,
        "population":population,
        "generations":generations,
        "spread_atr_assumption":spread_atr,"extra_fee_r_assumption":fee_r,
        "intrabar_ambiguity":"STOP_FIRST",
        "held_out_was_used_in_selection":False,
        "evaluations_are_independent_forward":False,
        "broker_fill_prices_verified":False,
        "candidate_rules":results,
        "orders_sent":0,
        "code_rewrite_permitted":False,
        "model_promotion_permitted":False,
        "live_execution_authorized":False,
        "production_action":"WAIT",
    }
