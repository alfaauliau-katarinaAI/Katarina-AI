"""Offline strategy-choice brain: expected R after costs, not a fixed win-rate gate.

Fits only on development periods. Outputs research recommendations, never broker
orders or risk authorization. Final-window rejection cannot select a replacement.
"""
from dataclasses import dataclass, asdict
from math import isfinite, sqrt
from statistics import mean, stdev
from collections import defaultdict
from hashlib import sha256
import json

@dataclass(frozen=True)
class StrategyObservation:
    sample_id: str
    candidate: str
    side: str
    regime: str
    entry_ns: int
    known_ns: int
    net_r: float
    def __post_init__(self):
        if not self.sample_id or not self.candidate or self.side not in ("BUY","SELL"):
            raise ValueError("invalid observation identity")
        if self.regime not in ("UP","DOWN","MIXED"):
            raise ValueError("unsupported regime")
        if self.entry_ns <= 0 or self.known_ns <= self.entry_ns or not isfinite(self.net_r):
            raise ValueError("invalid observation economics/time")

def stats(rows, extra_cost_r=.1):
    values=[r.net_r-extra_cost_r for r in rows]
    wins=sum(v for v in values if v>0);losses=-sum(v for v in values if v<0)
    daily=defaultdict(list)
    for r,v in zip(rows,values): daily[r.entry_ns//86_400_000_000_000].append(v)
    days=[sum(v) for v in daily.values()]
    return dict(trades=len(values),days=len(days),
                expectancy_r=mean(values) if values else None,
                net_r=sum(values),profit_factor=wins/losses if losses else None,
                win_rate=sum(v>0 for v in values)/len(values) if values else None,
                # Descriptive uncertainty diagnostic, not independent-day proof.
                daily_mean_minus_2se=mean(days)-2*stdev(days)/sqrt(len(days)) if len(days)>1 else None)

@dataclass(frozen=True)
class StrategyChoice:
    side: str
    regime: str
    candidate: str
    training: dict
    selection: dict

class StrategySelectionBrain:
    def __init__(self,min_train=30,min_selection=20,stress_r=.1,min_selection_pf=1.1):
        if min_train<10 or min_selection<10 or not isfinite(stress_r) or stress_r<0:
            raise ValueError("invalid selection policy")
        if not isfinite(min_selection_pf) or min_selection_pf<1:
            raise ValueError("invalid profit factor requirement")
        self.min_train=min_train;self.min_selection=min_selection
        self.stress_r=stress_r;self.min_selection_pf=min_selection_pf
        self.choices={};self.diagnostics=[];self.frozen_hash=None

    def fit(self,rows,*,train_cutoff_ns,selection_end_ns):
        if train_cutoff_ns<=0 or selection_end_ns<=train_cutoff_ns:
            raise ValueError("invalid chronological boundaries")
        rows=tuple(rows)
        if len({r.sample_id for r in rows})!=len(rows): raise ValueError("duplicate observation")
        # Defense in depth: all labels known after development are ignored.
        train=[r for r in rows if r.entry_ns<train_cutoff_ns and r.known_ns<train_cutoff_ns]
        selection=[r for r in rows if train_cutoff_ns<=r.entry_ns<selection_end_ns and r.known_ns<selection_end_ns]
        self.choices={};self.diagnostics=[]
        self.selection_end_ns=selection_end_ns
        for side in ("BUY","SELL"):
            for regime in ("UP","DOWN","MIXED"):
                eligible=[]
                ids=sorted({r.candidate for r in train if r.side==side and r.regime==regime})
                for candidate in ids:
                    a=stats([r for r in train if (r.side,r.regime,r.candidate)==(side,regime,candidate)],self.stress_r)
                    b=stats([r for r in selection if (r.side,r.regime,r.candidate)==(side,regime,candidate)],self.stress_r)
                    reasons=[]
                    if a["trades"]<self.min_train: reasons.append("insufficient_training")
                    if b["trades"]<self.min_selection: reasons.append("insufficient_selection")
                    if a["net_r"]<=0: reasons.append("nonpositive_training_after_stress")
                    if b["net_r"]<=0: reasons.append("nonpositive_selection_after_stress")
                    if b["profit_factor"] is None or b["profit_factor"]<self.min_selection_pf:
                        reasons.append("selection_profit_factor_not_established")
                    if a["days"]<5 or b["days"]<5: reasons.append("insufficient_day_coverage")
                    self.diagnostics.append(dict(side=side,regime=regime,candidate=candidate,
                                                 train=a,selection=b,reasons=reasons))
                    if not reasons:
                        eligible.append(StrategyChoice(side,regime,candidate,a,b))
                if eligible:
                    # Maximize weakest-window expected R; deterministic tie-breaking.
                    eligible.sort(key=lambda c:(-min(c.training["expectancy_r"],c.selection["expectancy_r"]),c.candidate))
                    self.choices[(side,regime)]=eligible[0]
        snapshot=dict(train_cutoff_ns=train_cutoff_ns,selection_end_ns=selection_end_ns,
                      min_train=self.min_train,min_selection=self.min_selection,
                      stress_r=self.stress_r,min_selection_pf=self.min_selection_pf,
                      choices=[asdict(c) for c in self.choices.values()])
        self.frozen_hash=sha256(json.dumps(snapshot,sort_keys=True,allow_nan=False).encode()).hexdigest()
        return dict(**snapshot,policy_sha256=self.frozen_hash,diagnostics=self.diagnostics,
                    research_only=True,live_risk_authorized=False,validated_strategy=False)

    def recommend(self,side,regime):
        choice=self.choices.get((side,regime))
        if choice is None:
            return dict(action="NO_TRADE",candidate=None,reason="no_eligible_strategy_for_state",
                        research_only=True,live_risk_authorized=False)
        return dict(action="RESEARCH_CANDIDATE",candidate=choice.candidate,
                    expected_r_after_stress=choice.selection["expectancy_r"],
                    reason="positive_development_and_selection_expectancy",
                    policy_sha256=self.frozen_hash,research_only=True,live_risk_authorized=False)

    def audit_final(self,rows,*,final_start_ns,final_end_ns):
        if not self.frozen_hash: raise ValueError("fit and freeze before final audit")
        if final_start_ns<self.selection_end_ns or final_end_ns<=final_start_ns:
            raise ValueError("final window must follow development")
        rows=tuple(rows);result=[]
        for (side,regime),choice in sorted(self.choices.items()):
            picked=[r for r in rows if r.candidate==choice.candidate and r.side==side and r.regime==regime
                    and final_start_ns<=r.entry_ns<final_end_ns and r.known_ns<final_end_ns]
            m=stats(picked,self.stress_r)
            passed=m["trades"]>=self.min_selection and m["days"]>=5 and m["net_r"]>0
            result.append(dict(side=side,regime=regime,candidate=choice.candidate,metrics=m,
                               result="PASS_RESEARCH_SCREEN" if passed else "REJECTED"))
        return dict(policy_sha256=self.frozen_hash,cells=result,research_only=True,
                    live_risk_authorized=False,validated_strategy=False,
                    limitation="Independent family runs do not simulate a combined router's position availability.")
