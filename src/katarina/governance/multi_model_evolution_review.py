"""G0DM0D3-inspired multi-model review interchange, gstack-inspired freshness.

Models may independently critique a *frozen* statistical proposal. This
module only accepts auditable verdicts; it never sends prompts, executes model
output, edits code, changes policy, or authorizes live trading. Third-party
LLM integrations are OPTIONAL and NOT silently enabled by this adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True,slots=True)
class IndependentModelVerdict:
    provider: str
    model: str
    proposal_receipt_sha256: str
    verdict: str
    evidence_references: tuple[str,...]
    # No raw code/prompt executes from this field. Bounded text only.
    rationale: str = ""


@dataclass(frozen=True,slots=True)
class MultiModelReviewResult:
    status: str
    independent_providers: int
    valid_reviews: int
    blockers: tuple[str,...]
    review_fingerprint_sha256: str
    research_only: bool = True
    code_mutation_authorized: bool = False
    real_execution_authorized: bool = False

    def to_dict(self) -> dict:
        return {
            "status":self.status,
            "independent_providers":self.independent_providers,
            "valid_reviews":self.valid_reviews,
            "blockers":list(self.blockers),
            "review_fingerprint_sha256":self.review_fingerprint_sha256,
            "research_only":True,
            "code_mutation_authorized":False,
            "real_execution_authorized":False,
        }


def review_candidate(report: dict,
                     external_verdicts: tuple[IndependentModelVerdict,...] = ()
                     ) -> MultiModelReviewResult:
    """Research review *only*, with content fingerprint and vendor diversity."""
    receipt = report.get("review_receipt_sha256", "")
    if (not isinstance(receipt,str) or len(receipt)!=64 or
            not all(c in "0123456789abcdef" for c in receipt)):
        raise ValueError("unverified_source_fingerprint")
    if len(external_verdicts)>8:
        raise ValueError("unbounded_review_set")
    seen_models=set()
    providers=set()
    blockers=[]
    normalized=[]
    for vote in external_verdicts:
        if not isinstance(vote,IndependentModelVerdict):
            blockers.append("malformed_model_verdict")
            continue
        if (vote.proposal_receipt_sha256!=receipt or
                vote.verdict not in ("APPROVE_RESEARCH","REJECT","ABSTAIN") or
                len(vote.provider)>100 or len(vote.model)>100 or
                not vote.provider or not vote.model or
                len(vote.rationale)>600 or
                not vote.evidence_references or
                len(vote.evidence_references)>20 or
                any(not isinstance(x,str) or len(x)>200
                    for x in vote.evidence_references)):
            blockers.append("stale_or_invalid_model_verdict")
            continue
        identity=(vote.provider.lower(),vote.model.lower())
        if identity in seen_models:
            blockers.append("duplicate_model_verdict")
            continue
        seen_models.add(identity)
        providers.add(vote.provider.lower())
        normalized.append({
            "provider":vote.provider.lower(),"model":vote.model.lower(),
            "verdict":vote.verdict,
            "evidence_references":vote.evidence_references,
            "rationale":vote.rationale,
        })
    if not external_verdicts:
        blockers.append("no_external_models_connected")
    if len(providers)<2:
        blockers.append("two_independent_providers_required")
    if report.get("decision")!="RESEARCH_PROPOSAL_ONLY":
        blockers.append("statistical_research_candidate_not_ready")
    if any(v["verdict"]!="APPROVE_RESEARCH" for v in normalized):
        blockers.append("model_dissent_or_abstention")
    if any(not v["evidence_references"] for v in normalized):
        blockers.append("no_cited_review_evidence")
    if any(not v.get("pass") for v in report.get("reviewers",[])
           if v.get("reviewer") in ("data_integrity", "quant_out_of_sample")):
        blockers.append("statistical_or_data_review_not_passed")
    # Broker execution and engineering release critics remain blocked, but
    # are not needed to merely propose another isolated research experiment.

    material={"source_receipt":receipt,"votes":sorted(
        normalized,key=lambda x:(x["provider"],x["model"])),
        "blockers":sorted(set(blockers))}
    fingerprint=sha256(json.dumps(material,sort_keys=True,
        separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
    status=("RESEARCH_IDEA_READY_FOR_ADDITIONAL_TESTS" if not blockers
            else "REVIEW_BLOCKED")
    return MultiModelReviewResult(
        status=status,independent_providers=len(providers),
        valid_reviews=len(normalized),
        blockers=tuple(sorted(set(blockers))),
        review_fingerprint_sha256=fingerprint,
    )
