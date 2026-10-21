from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from katarina.intelligence.perception.xauusd import XauusdAssessment
from katarina.engines.scalper_entry import EntryProposal, EntrySide

class DecisionAction(str, Enum):
    BUY="BUY"; SELL="SELL"; NO_TRADE="NO_TRADE"; WAIT="WAIT"; SAFE_MODE="SAFE_MODE"

@dataclass(frozen=True, slots=True)
class TradeCandidate:
    action: DecisionAction
    score: float
    uncertainty: float
    reasons: tuple[str, ...]
    invalidation: str
    expected_rr: float
    live_risk_authorized: bool=False

class DecisionEngine:
    def decide(self, assessment: XauusdAssessment, *, expected_rr: float, system_healthy: bool, min_score: float=0.65, max_uncertainty: float=0.40) -> TradeCandidate:
        if not system_healthy:
            return TradeCandidate(DecisionAction.SAFE_MODE,0.0,1.0,("system_unhealthy",),"health_restored",0.0,False)
        if not assessment.valid_domain:
            return TradeCandidate(DecisionAction.NO_TRADE,assessment.score,assessment.uncertainty,assessment.reasons,"validated_domain_restored",0.0,False)
        if expected_rr<=0 or assessment.score<min_score or assessment.uncertainty>max_uncertainty or assessment.bias==0:
            return TradeCandidate(DecisionAction.NO_TRADE,assessment.score,assessment.uncertainty,assessment.reasons,"evidence_improves",max(0.0,expected_rr),False)
        action=DecisionAction.BUY if assessment.bias>0 else DecisionAction.SELL
        return TradeCandidate(action,assessment.score,assessment.uncertainty,assessment.reasons,"specialist_bias_invalidated",expected_rr,False)

    def decide_scalper(self, proposal: EntryProposal, *, system_healthy: bool, min_score: float=0.65, max_uncertainty: float=0.40) -> TradeCandidate:
        if not system_healthy:
            return TradeCandidate(DecisionAction.SAFE_MODE,0.0,1.0,("system_unhealthy",),"health_restored",0.0,False)
        if not proposal.valid or proposal.side is EntrySide.NONE:
            return TradeCandidate(DecisionAction.NO_TRADE,proposal.score,proposal.uncertainty,proposal.reasons,"new_valid_entry_proposal",0.0,False)
        if proposal.score < min_score or proposal.uncertainty > max_uncertainty or proposal.expected_rr <= 0:
            return TradeCandidate(DecisionAction.NO_TRADE,proposal.score,proposal.uncertainty,proposal.reasons,"entry_quality_improves",max(0.0,proposal.expected_rr),False)
        action=DecisionAction.BUY if proposal.side is EntrySide.BUY else DecisionAction.SELL
        return TradeCandidate(action,proposal.score,proposal.uncertainty,proposal.reasons,"entry_setup_invalidated",proposal.expected_rr,False)
