"""Bounded, deterministic self-improvement lab using genuine prospective quote observations.

Inspired by gstack's evidence-fresh review gates and G0DM0D3's independent
reviewer pattern. No external code is copied, no LLM/provider credentials
required, no process execution, code mutation, orders, or promotion.

This is a *research learning system*: trained threshold proposals are
chronologically checked on later shadow observations; those observations are
NOT broker executions and can NEVER authorize risk.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite, sqrt
from statistics import mean, stdev
import json
import sqlite3

VERSION = "KATARINA_SHADOW_SELF_EVOLUTION_V1"
THRESHOLDS = (0.62, 0.70, 0.78)
MIN_TRAIN = 60
MIN_HOLDOUT = 30
MIN_TRAIN_DAYS = 8
MIN_HOLDOUT_DAYS = 5
MIN_COVERAGE = 0.80
MAX_ROWS = 3500


def _digest(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def _utc_day(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).date().isoformat()


def _lower_by_day(rows: list[dict]) -> float | None:
    """Daily cluster lower bound; not a calibrated independent-trade bound."""
    days = defaultdict(list)
    for row in rows:
        days[_utc_day(row["observed"])].append(row["net_r"])
    if len(days) < 2:
        return None
    daily = [mean(v) for v in days.values()]
    return mean(daily) - 1.96 * stdev(daily) / sqrt(len(daily))


def _metric(rows: list[dict]) -> dict:
    p = sum(r["net_r"] for r in rows if r["net_r"] > 0)
    n = -sum(r["net_r"] for r in rows if r["net_r"] < 0)
    return {
        "observations": len(rows),
        "days": len({_utc_day(r["observed"]) for r in rows}),
        "mean_modelled_r": round(mean([r["net_r"] for r in rows]), 6) if rows else None,
        "daily_cluster_lower_r": (round(x, 6) if
            (x := _lower_by_day(rows)) is not None else None),
        "virtual_profit_factor": round(p/n, 6) if n > 0 else None,
    }


def _read(db: sqlite3.Connection, as_of: float) -> tuple[list[dict], str | None]:
    try:
        data = db.execute(
            """SELECT id,symbol,method,side,regime,observed_at,exit_at,
                      state,virtual_net_r,evidence_score,official_news_verified
               FROM prospective_shadow WHERE observed_at<=?
               ORDER BY observed_at DESC,id DESC LIMIT ?""",
            (as_of, MAX_ROWS + 1),
        ).fetchall()
    except sqlite3.OperationalError:
        return [], "prospective_shadow_schema_unavailable"
    # Never silently drop older rows and then treat the surviving recent
    # window as an unbiased cohort. Require explicitly bounded evidence.
    if len(data) > MAX_ROWS:
        return [], "shadow_observation_window_truncated"

    clean = []
    seen = set()
    causal_identities = set()
    for raw in data:
        oid, symbol, method, side, regime, observed, exited, status, value, score, news = raw
        if oid in seen:
            return [], "duplicate_observation_identity"
        seen.add(oid)
        if (not isinstance(oid, int) or not all(isinstance(x,str) and x
                for x in (symbol,method,side,regime)) or
                side not in ("BUY","SELL") or
                not isinstance(observed,(float,int)) or not isfinite(observed) or
                observed <= 0 or observed > as_of or
                not isinstance(score,(float,int)) or not isfinite(score) or
                not 0 <= score <= 1 or status not in
                ("OPEN", "UNCERTAIN_GAP", "VIRTUAL_QUOTED")):
            return [], "invalid_shadow_observation"
        # Separate SQL row IDs do not make a repeated symbol/method/side/
        # regime/observation instant an independent market event.
        identity = (symbol, method, side, regime, float(observed))
        if identity in causal_identities:
            return [], "duplicate_causal_shadow_observation"
        causal_identities.add(identity)
        if status == "VIRTUAL_QUOTED":
            if (not isinstance(exited,(float,int)) or not isfinite(exited) or
                    exited < observed or exited > as_of or
                    not isinstance(value,(float,int)) or not isfinite(value) or
                    abs(value) > 100):
                return [], "invalid_or_future_outcome"
        elif status == "UNCERTAIN_GAP":
            if (exited is None or not isinstance(exited,(float,int)) or
                    not isfinite(exited) or exited < observed or exited > as_of or
                    value is not None):
                return [], "invalid_uncertain_gap"
        elif exited is not None or value is not None:
            return [], "open_outcome_leakage"
        clean.append({
            "id":oid, "symbol":symbol, "method":method, "side":side,
            "regime":regime, "observed":float(observed),
            "exited":float(exited) if exited is not None else None,
            "status":status, "net_r":float(value) if value is not None else None,
            "score":float(score), "news_verified":bool(news),
        })
    clean.reverse()
    return clean, None


def _research_cohort(group: list[dict], key: tuple[str,...]) -> dict:
    out = {
        "symbol":key[0], "method":key[1], "side":key[2], "regime":key[3],
        "recorded":len(group), "status":"INSUFFICIENT_EVIDENCE",
        "proposed_min_evidence_score":None, "promotion_allowed":False,
        "real_broker_fills_verified":False,
    }
    # Entire cohort is retained in quality checks: never silently discard
    # gaps or failures to create a profitable-looking filtered subset.
    matured = [r for r in group if r["status"] != "OPEN"]
    good = [r for r in matured if r["status"] == "VIRTUAL_QUOTED"]
    coverage = len(good)/len(matured) if matured else None
    out["completed"] = len(good)
    out["gapped"] = len(matured)-len(good)
    out["pending"] = len(group)-len(matured)
    out["coverage"] = round(coverage, 6) if coverage is not None else None
    out["baseline"] = _metric(good)
    days = sorted({_utc_day(r["observed"]) for r in group})
    if (coverage is None or coverage < MIN_COVERAGE or len(days) <
            MIN_TRAIN_DAYS+MIN_HOLDOUT_DAYS or len(good) <
            MIN_TRAIN+MIN_HOLDOUT):
        return out
    split_day = days[int(len(days) * .70)]
    split_epoch = datetime.fromisoformat(split_day).replace(
        tzinfo=timezone.utc).timestamp()
    train = [r for r in good if r["observed"] < split_epoch and
             r["exited"] < split_epoch]
    holdout = [r for r in good if r["observed"] >= split_epoch]
    out["holdout_from_day_utc"] = split_day
    if (len(train) < MIN_TRAIN or len(holdout) < MIN_HOLDOUT or
            len({_utc_day(r["observed"]) for r in train}) < MIN_TRAIN_DAYS or
            len({_utc_day(r["observed"]) for r in holdout}) < MIN_HOLDOUT_DAYS):
        return out

    candidates = []
    for cutoff in THRESHOLDS:
        sample = [r for r in train if r["score"] >= cutoff]
        metrics = _metric(sample)
        lb = metrics["daily_cluster_lower_r"]
        if (len(sample) < MIN_TRAIN or metrics["days"] < MIN_TRAIN_DAYS or
                lb is None):
            continue
        # Shrink towards slightly negative pre-cost prior; historical
        # parameter selection is an exploratory policy, not alpha proof.
        shrunken = (sum(r["net_r"] for r in sample) - 1.0)/(len(sample)+20)
        candidates.append((shrunken, -cutoff, cutoff, metrics))
    if not candidates:
        return out
    _, _, chosen, training = max(candidates)
    untouched = [r for r in holdout if r["score"] >= chosen]
    hold = _metric(untouched)
    out["training"] = training
    out["holdout"] = hold
    out["proposed_min_evidence_score"] = chosen
    if (hold["observations"] < MIN_HOLDOUT or
            hold["days"] < MIN_HOLDOUT_DAYS):
        out["status"] = "HOLDOUT_INSUFFICIENT"
        return out
    if (training["daily_cluster_lower_r"] <= 0 or
            hold["daily_cluster_lower_r"] is None or
            hold["daily_cluster_lower_r"] <= 0 or
            hold["mean_modelled_r"] <= 0):
        out["status"] = "UNSTABLE_OR_NEGATIVE_QUOTE_EDGE"
    else:
        out["status"] = "RESEARCH_CANDIDATE_REVIEW_REQUIRED"
    return out


def _independent_critics(report: dict) -> list[dict]:
    """Independent deterministic critics, NOT impersonated external LLM votes."""
    valid = report["data_integrity"] == "VALID"
    positive = any(c["status"]=="RESEARCH_CANDIDATE_REVIEW_REQUIRED"
                   for c in report["cohorts"])
    votes = (
        ("data_integrity", valid, "past-only observations and schema validated"),
        ("quant_out_of_sample", positive,
         "chronological train/held-out quote diagnostics positive"),
        ("broker_execution", False,
         "virtual quotes are not broker fills; costs unverified"),
        ("engineering_review", False,
         "no fresh code-diff review, regression receipt or approved promotion"),
    )
    return [{"reviewer":name, "pass":result, "reason":reason,
             "mechanism":"DETERMINISTIC_POLICY_NOT_LLM"}
            for name,result,reason in votes]


def evaluate_shadow_self_evolution(
    db: sqlite3.Connection, *, as_of_utc: datetime,
) -> dict:
    """Pure read-only learner that emits reproducible research proposals."""
    if not isinstance(as_of_utc,datetime) or as_of_utc.tzinfo is None:
        raise ValueError("timezone_aware_as_of_required")
    as_of = as_of_utc.astimezone(timezone.utc)
    rows, issue = _read(db,as_of.timestamp())
    groups: dict[tuple[str,...],list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["symbol"],r["method"],r["side"],r["regime"])].append(r)
    cohorts = [_research_cohort(v,k) for k,v in
               sorted(groups.items(),key=lambda kv:(-len(kv[1]),kv[0]))[:20]]
    report = {
        "version": VERSION, "as_of_utc": as_of.isoformat(),
        "learning_mode":"CHRONOLOGICAL_OUT_OF_SAMPLE_QUOTE_RESEARCH",
        "source":"PROSPECTIVE_SHADOW_BROKER_BID_ASK_VIRTUAL_QUOTES",
        "data_integrity":"INVALID" if issue else "VALID",
        "error":issue, "rows_read":len(rows),
        "cohorts":cohorts,
        "external_models_invoked":0,
        "model_feedback_adapter":"NOT_CONFIGURED",
        "historical_optimisation_is_real_forward":False,
        "costs_and_broker_fills_verified":False,
        "order_submission_authorized":False,
        "self_code_mutation_authorized":False,
        "live_risk_authorized_fraction":0.0,
    }
    report["reviewers"]=_independent_critics(report)
    report["decision"]=(
        "RESEARCH_PROPOSAL_ONLY" if
        any(c["status"]=="RESEARCH_CANDIDATE_REVIEW_REQUIRED"
            for c in cohorts) and not issue
        else "WAIT_FOR_VERIFIED_EVIDENCE")
    report["promotion_allowed"]=False
    report["source_digest_sha256"]=_digest({
        "version":VERSION, "as_of":as_of.isoformat(),
        "rows":rows,
    })
    report["review_receipt_sha256"]=_digest({
        "source_digest":report["source_digest_sha256"],
        "decision":report["decision"],"cohorts":cohorts,
        "reviewers":report["reviewers"], "version":VERSION,
    })
    return report


@dataclass(frozen=True, slots=True)
class ShadowResearchPolicy:
    """Evolving observation filter for ONE existing virtual-shadow book.

    It may narrow which hypotheses are sampled in research. It cannot
    change live risk, trade orders, production weights, or source code.
    """
    source_digest_sha256: str
    review_receipt_sha256: str
    as_of_utc: str
    integrity_ok: bool
    rules: tuple[tuple[str,str,str,str,float,str], ...]
    default_min_score: float = 0.62
    live_execution_authorized: bool = False

    def score_floor(self, symbol: str, method: str,
                    side: str, regime: str) -> float:
        if not self.integrity_ok:
            return 1.01  # no research entries from corrupt evidence
        for sym, meth, direction, state, floor, _ in self.rules:
            if (sym,meth,direction,state)==(symbol,method,side,regime):
                return floor
        return self.default_min_score

    def to_dict(self) -> dict:
        return {
            "mode":"CAUSAL_SHADOW_FEEDBACK_RESEARCH_ONLY",
            "as_of_utc":self.as_of_utc,
            "source_digest_sha256":self.source_digest_sha256,
            "review_receipt_sha256":self.review_receipt_sha256,
            "integrity_ok":self.integrity_ok,
            "default_min_score":self.default_min_score,
            "cohorts":[{
                "symbol":sym,"method":method,"side":side,"regime":regime,
                "observational_score_floor":score,"reason":reason,
            } for sym,method,side,regime,score,reason in self.rules],
            "may_change_real_orders":False,
            "may_change_production_model":False,
            "may_authorize_live":False,
        }


def derive_shadow_research_policy(report: dict) -> ShadowResearchPolicy:
    """Close feedback loop on mature quote-only observations, conservatively.

    Every side / strategy / regime learns separately. Poor prospective quote
    outcomes quarantine sampling to a high threshold; favorable held-out
    quotes MAY narrow the virtual sampling threshold. Unknown cohorts keep the
    old baseline. No outcome can lower a floor or promote a real strategy.
    """
    if not isinstance(report, dict):
        raise ValueError("invalid_shadow_learning_report")
    valid = report.get("data_integrity") == "VALID"
    cohorts = report.get("cohorts")
    if not isinstance(cohorts,list):
        valid=False
        cohorts=[]
    proposals=[]
    if valid:
        for row in cohorts:
            if not isinstance(row,dict):
                valid=False
                break
            key=tuple(row.get(x) for x in ("symbol","method","side","regime"))
            if (any(not isinstance(x,str) or not x for x in key)
                    or key[2] not in ("BUY","SELL")):
                valid=False
                break
            status=row.get("status")
            floor=.62
            reason="AWAIT_MATURE_PROSPECTIVE_OUTCOMES"
            if status == "RESEARCH_CANDIDATE_REVIEW_REQUIRED":
                proposed=row.get("proposed_min_evidence_score")
                if type(proposed) not in (int,float) or not isfinite(proposed):
                    valid=False
                    break
                floor=max(.62,min(.95,float(proposed)))
                reason="HELD_OUT_VIRTUAL_SCORE_THRESHOLD_REVIEW_ONLY"
            elif status == "UNSTABLE_OR_NEGATIVE_QUOTE_EDGE":
                # Reduces exploration of apparently poor research cohorts;
                # never forces the opposite BUY/SELL decision.
                floor=.78
                reason="NEGATIVE_VIRTUAL_OUTCOMES_CONSERVATIVE_QUARANTINE"
            elif status in ("HOLDOUT_INSUFFICIENT","INSUFFICIENT_EVIDENCE"):
                pass
            else:
                valid=False
                break
            proposals.append((*key,floor,reason))
    if not valid:
        proposals=[]
    asof=report.get("as_of_utc","")
    source=report.get("source_digest_sha256","")
    receipt=report.get("review_receipt_sha256","")
    if not (isinstance(asof,str) and isinstance(source,str)
            and isinstance(receipt,str) and len(source)==64
            and len(receipt)==64):
        valid=False
        proposals=[]
    return ShadowResearchPolicy(source if isinstance(source,str) else "",
                                receipt if isinstance(receipt,str) else "",
                                asof if isinstance(asof,str) else "",
                                valid,tuple(sorted(proposals)))
