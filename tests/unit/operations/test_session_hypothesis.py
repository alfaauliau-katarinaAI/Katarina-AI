"""Synthetic-only regression for proposed broker-session classification.

This never connects to MT5, alters the observer DB, or changes Stage0 scoring.
"""
import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[3] / "scripts/governance/session_hypothesis.py"
SPEC = importlib.util.spec_from_file_location("session_hypothesis", PATH)
h = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)


def policy():
    # Future-oriented example, NOT real broker schedule evidence.
    return {
        "schema_version": 1,
        "status": "HYPOTHESIS_ONLY",
        "proposal_created_utc": "2030-10-30T12:00:00+00:00",
        "future_effective_utc": "2030-10-31T00:00:00+00:00",
        "expiry_utc": "2030-11-08T00:00:00+00:00",
        "candidate_closed_windows_utc": {
            "XAUUSD.vx": [
                ["2030-10-31T21:00:00Z", "2030-10-31T22:00:00Z"],
                ["2030-11-04T22:00:00Z", "2030-11-04T23:00:00Z"],
            ],
            "NAS100.vx": [
                ["2030-10-31T21:00:00Z", "2030-10-31T22:00:00Z"],
                ["2030-11-04T22:00:00Z", "2030-11-04T23:00:00Z"],
            ],
            "EURUSD.vx": [],
        },
    }


class SessionHypothesisTests(unittest.TestCase):
    def test_utc_closed_window_boundaries_are_half_open(self):
        p = policy()
        self.assertEqual(h.classify_hypothesis("XAUUSD.vx", "2030-11-04T22:00:00Z", p), "HYPOTHETICAL_CLOSED")
        self.assertEqual(h.classify_hypothesis("XAUUSD.vx", "2030-11-04T22:59:59Z", p), "HYPOTHETICAL_CLOSED")
        self.assertEqual(h.classify_hypothesis("XAUUSD.vx", "2030-11-04T23:00:00Z", p), "UNVERIFIED")

    def test_different_windows_before_and_after_dst_are_explicit(self):
        p = policy()
        self.assertEqual(h.classify_hypothesis("NAS100.vx", "2030-10-31T21:30:00Z", p), "HYPOTHETICAL_CLOSED")
        self.assertEqual(h.classify_hypothesis("NAS100.vx", "2030-11-04T22:30:00Z", p), "HYPOTHETICAL_CLOSED")
        self.assertEqual(h.classify_hypothesis("NAS100.vx", "2030-11-04T21:30:00Z", p), "UNVERIFIED")

    def test_mixed_forex_and_missing_symbol_does_not_infer_closed(self):
        p = policy()
        self.assertEqual(h.classify_hypothesis("EURUSD.vx", "2030-11-04T22:30:00Z", p), "UNVERIFIED")
        self.assertEqual(h.classify_hypothesis("USDJPY.vx", "2030-11-04T22:30:00Z", p), "UNVERIFIED")

    def test_outside_proposal_coverage_never_becomes_closed(self):
        p = policy()
        self.assertEqual(h.classify_hypothesis("XAUUSD.vx", "2030-10-30T21:30:00Z", p), "UNVERIFIED")
        self.assertEqual(h.classify_hypothesis("XAUUSD.vx", "2030-11-08T00:00:00Z", p), "UNVERIFIED")

    def test_unapproved_status_cannot_be_passed_off_as_accepted_policy(self):
        p = policy()
        p["status"] = "APPROVED"
        with self.assertRaisesRegex(ValueError, "NO_AUTHORIZED_SESSION_POLICY"):
            h.classify_hypothesis("XAUUSD.vx", "2030-11-04T22:30:00Z", p)

    def test_retroactive_effective_time_is_rejected(self):
        p = policy()
        p["future_effective_utc"] = p["proposal_created_utc"]
        with self.assertRaisesRegex(ValueError, "RETROACTIVE_EFFECTIVE_TIME"):
            h.validate_hypothesis(p)

    def test_missing_timezone_is_rejected(self):
        p = policy()
        p["proposal_created_utc"] = "2030-10-30T12:00:00"
        with self.assertRaisesRegex(ValueError, "AWARE_UTC_REQUIRED"):
            h.validate_hypothesis(p)

    def test_overlapping_windows_rejected(self):
        p = policy()
        p["candidate_closed_windows_utc"]["XAUUSD.vx"].insert(
            1, ["2030-10-31T21:30:00Z", "2030-10-31T21:45:00Z"]
        )
        with self.assertRaisesRegex(ValueError, "OVERLAPPING_OR_UNSORTED_WINDOWS"):
            h.validate_hypothesis(p)

    def test_out_of_range_and_long_window_rejected(self):
        p = policy()
        p["candidate_closed_windows_utc"]["XAUUSD.vx"][0] = [
            "2030-10-31T21:00:00Z", "2030-11-01T02:00:00Z"
        ]
        with self.assertRaisesRegex(ValueError, "UNSAFE_CLOSED_WINDOW"):
            h.validate_hypothesis(p)

    def test_weekend_without_evidence_is_unverified(self):
        p = policy()
        self.assertEqual(h.classify_hypothesis("XAUUSD.vx", "2030-11-02T12:00:00Z", p), "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
