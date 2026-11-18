"""P9 V2 Robust FIVE pure research risk calculator; NEVER executable."""
from dataclasses import dataclass
from pathlib import Path
import json
import math

ENGINES=("XAU_H1_BUY","XAU_H4_BUY","NAS_H4_SELL","EUR_H4_BUY","CHF_H4_BUY")
FAMILIES=("XAU","NAS","EUR","CHF")
NATIVE_CAP=.25

@dataclass(frozen=True)
class ShadowQuote:
    engine:str
    profile:str
    family:str
    adr_ratio:float
    paper_risk_pct:float
    hypothetical_loss_usd:float
    authorized_live_risk_pct:float=0.0
    can_send_orders:bool=False
    evidence_gate:str="WAIT"

def load_candidate(path):
    item=json.loads(Path(path).read_text(encoding="utf8"))
    gate=item.get("risk_allocation",{})
    if (item.get("status")!="INTEGRATED_SHADOW_RESEARCH_NOT_PRODUCTION"
        or gate.get("live_authorized") is not False
        or gate.get("risk_sizing_not_executable") is not True
        or gate.get("evidence_gate")!="WAIT"
        or gate.get("native_live_cap_pct_per_entry")!=NATIVE_CAP):
        raise PermissionError("P9_V2_ROBUST_PRODUCTION_FORBIDDEN")
    if tuple(item.get("engines",[]))!=ENGINES:
        raise ValueError("P9_V2_ROBUST_FIVE_ENGINES_ONLY")
    if item.get("selected") not in item.get("profiles",{}):
        raise ValueError("P9_V2_ROBUST_SELECTED_PROFILE_MISSING")
    for prof in item["profiles"].values():
        risk=prof.get("base_risk_pct_by_family",{})
        rule=prof.get("adr",{})
        if set(risk)!=set(FAMILIES):
            raise ValueError("P9_V2_ROBUST_FAMILY_MISMATCH")
        for v in risk.values():
            if type(v) not in (int,float) or not math.isfinite(v) or not (0<v<=12):
                raise ValueError("P9_V2_ROBUST_INVALID_PERCENT")
        for k in ("threshold_low","threshold_high","factor_low","factor_mid","factor_high"):
            v=rule.get(k)
            if type(v) not in (int,float) or not math.isfinite(v) or v<=0:
                raise ValueError("P9_V2_ROBUST_INVALID_ADR")
        if rule["threshold_low"]>=rule["threshold_high"]:
            raise ValueError("P9_V2_ROBUST_BANDS_INVALID")
        if rule.get("measure") not in ("ADR20_OVER_ADR100","ADR20_OVER_PRIOR_EXPANDING_MEDIAN_ADR20"):
            raise ValueError("P9_V2_ROBUST_MEASURE_INVALID")
        if not isinstance(rule.get("targets"),list) or not set(rule["targets"]).issubset(FAMILIES):
            raise ValueError("P9_V2_ROBUST_TARGET_INVALID")
    return item

def quote_research_only(data, *, engine, adr_ratio, balance_usd,
                        closed_dd_pct=0., profile=None, mode="RESEARCH_SHADOW"):
    """A hypothetical risk budget, NOT lots, trade orders or live permission.

    adr_ratio MUST be computed only from completed trading days before entry.
    """
    if mode!="RESEARCH_SHADOW":
        raise PermissionError("P9_V2_ROBUST_LIVE_AND_DEMO_FORBIDDEN")
    gate=data.get("risk_allocation",{})
    if (data.get("status")!="INTEGRATED_SHADOW_RESEARCH_NOT_PRODUCTION"
        or gate.get("live_authorized") is not False or gate.get("evidence_gate")!="WAIT"
        or gate.get("risk_sizing_not_executable") is not True):
        raise PermissionError("P9_V2_ROBUST_NO_PROMOTION")
    if engine not in ENGINES:
        raise ValueError("P9_V2_ROBUST_UNKNOWN_ENGINE")
    for val in (adr_ratio,balance_usd,closed_dd_pct):
        if type(val) not in (int,float) or not math.isfinite(val):
            raise ValueError("P9_V2_ROBUST_NONFINITE")
    if adr_ratio<=0 or balance_usd<=0 or not 0<=closed_dd_pct<=100:
        raise ValueError("P9_V2_ROBUST_INVALID_INPUT")
    name=profile or data["selected"]
    if name not in data["profiles"]:raise ValueError("P9_V2_ROBUST_UNKNOWN_PROFILE")
    family=engine.split("_")[0]
    item=data["profiles"][name];rule=item["adr"]
    mult=1.
    if family in rule["targets"]:
        if adr_ratio<rule["threshold_low"]:mult=rule["factor_low"]
        elif adr_ratio>=rule["threshold_high"]:mult=rule["factor_high"]
        else:mult=rule["factor_mid"]
    guard=0. if closed_dd_pct>=gate["dd_new_entry_stop_at_pct"] else (
        gate["dd_reduce_multiplier"] if closed_dd_pct>=gate["dd_reduce_at_pct"] else 1.)
    pct=round(item["base_risk_pct_by_family"][family]*mult*guard,8)
    return ShadowQuote(engine,name,family,float(adr_ratio),pct,round(balance_usd*pct/100,8))
