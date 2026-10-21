"""Offline regression for external model bridge."""
import json
import unittest
from katarina.governance.external_model_bridge import (
    brief_for_external_models, review_by_external_models,
    verdict_from_text,
)

REPORT = {
    "review_receipt_sha256": "a" * 64,
    "decision": "RESEARCH_PROPOSAL_ONLY",
    "cohorts": [{"symbol": "PRIVATE", "status": "RESEARCH_CANDIDATE_REVIEW_REQUIRED",
                 "recorded": 180, "coverage": 1., "proposed_min_evidence_score": .7,
                 "training": {"observations": 100, "mean_modelled_r": .3},
                 "holdout": {"observations": 80, "mean_modelled_r": .2}}],
    "reviewers": [{"reviewer": "data_integrity", "pass": True},
                  {"reviewer": "quant_out_of_sample", "pass": True}],
}

class FakeResponse:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *unused):
        return False
    def read(self, count):
        return self.data[:count]

def fake_transport(request, timeout):
    assert timeout == 25
    assert request.full_url == "https://models.github.ai/inference/chat/completions"
    body = json.loads(request.data)
    assert body["temperature"] == 0
    return FakeResponse(json.dumps({"choices": [{"message": {"content": json.dumps({
        "verdict": "APPROVE_RESEARCH",
        "rationale": "More offline evidence required.",
        "evidence_references": ["cohorts.0.holdout"],
    })}}]}).encode())

class ExternalModelTests(unittest.TestCase):
    def test_allowlisted_research_summary(self):
        brief = brief_for_external_models(REPORT)
        self.assertNotIn("PRIVATE", json.dumps(brief))
        self.assertEqual(brief["independently_verified_real_trades"], 0)

    def test_two_external_models_review_only(self):
        result = review_by_external_models(
            REPORT, "unit-fixture-token", ("openai/test", "meta/test"),
            transport=fake_transport)
        self.assertEqual(result["external_models_succeeded"], 2)
        self.assertEqual(result["research_review"]["status"],
                         "RESEARCH_IDEA_READY_FOR_ADDITIONAL_TESTS")
        self.assertFalse(result["live_execution_authorized"])
        self.assertFalse(result["self_code_mutation_authorized"])

    def test_token_missing_blocks(self):
        result = review_by_external_models(
            REPORT, "", ("openai/test", "meta/test"), transport=fake_transport)
        self.assertEqual(result["external_models_succeeded"], 0)
        self.assertEqual(result["research_review"]["status"], "REVIEW_BLOCKED")

    def test_unverifiable_source_cannot_approve(self):
        with self.assertRaises(ValueError):
            verdict_from_text(
                '{"verdict":"APPROVE_RESEARCH","rationale":"ok",'
                '"evidence_references":["invalid-link"]}',
                model="openai/test", receipt="a"*64)

    def test_same_vendor_disallowed(self):
        with self.assertRaises(ValueError):
            review_by_external_models(REPORT, "unit-fixture-token",
                                      ("openai/a", "openai/b"), fake_transport)
if __name__ == "__main__":
    unittest.main()
