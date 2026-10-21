"""Research-only tests for corrected selection and evidence gate."""
import unittest

from research.safety.reselection_guard import choose_candidate, evidence_gate


def row(setup, n22=25, n23=25, mean22=.12, mean23=.20,
        review_profit=0.0, future_count=100):
    return dict(pair="XAUUSD", setup=setup, threshold_scale="1.18",
                context_gate="ANY", exit="RUNNER_60",
                n22=n22, n23=n23, mean22=mean22, mean23=mean23,
                mean24=review_profit, mean25=review_profit,
                mean26=review_profit, n_exec=future_count,
                n_complete=future_count)


class SelectionGuardTests(unittest.TestCase):
    def test_future_outcomes_cannot_change_selection(self):
        a = [row("A", mean22=.2, mean23=.12), row("B", mean22=.10, mean23=.08)]
        first = choose_candidate(a)
        b = [dict(x) for x in a]
        b[1].update(mean24=999, mean25=999, mean26=999,
                    n_exec=1_000_000, n_complete=1_000_000)
        self.assertEqual(first["setup"], choose_candidate(b)["setup"])

    def test_no_dev_sample_fallback_ignores_review_counts(self):
        a = [row("A", n22=8, n23=9), row("B", n22=2, n23=3)]
        self.assertEqual(choose_candidate(a)["setup"], "A")
        a[1]["n_exec"] = 999999999
        self.assertEqual(choose_candidate(a)["setup"], "A")
        self.assertEqual(choose_candidate(a)["state"], "ABSTAIN_INSUFFICIENT_SAMPLE")

    def test_nominal_development_not_production_permission(self):
        result = evidence_gate(True, -.2, .2, -.3, False, False)
        self.assertEqual(result["decision"], "ABSTAIN")
        self.assertFalse(result["live_trading_authorized"])

    def test_all_checks_pass_is_still_research_only(self):
        result = evidence_gate(True, .05, .04, .03, True, True)
        self.assertEqual(result["decision"], "RESEARCH_ONLY")
        self.assertFalse(result["live_trading_authorized"])

    def test_none_is_always_invalid(self):
        with self.assertRaises(ValueError):
            choose_candidate([])


if __name__ == "__main__":
    unittest.main()
