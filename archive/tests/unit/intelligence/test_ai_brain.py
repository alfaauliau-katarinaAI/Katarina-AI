from __future__ import annotations

from dataclasses import replace
from math import nan
import unittest

from katarina.engines.decision import DecisionAction
from katarina.engines.opportunity import MarketCandidate
from katarina.engines.scalper_entry import EntryMode, EntryProposal, EntrySide
from katarina.engines.setup_quality import SetupQualityInput
from katarina.intelligence.brain import KatarinaAIBrain, LabeledMarketExample
from katarina.intelligence.market_universe import AssetClass, TradableInstrument
from katarina.intelligence.news_intelligence import NewsContext
from katarina.intelligence.regime import Regime, RegimeAssessment


def examples(count=70):
    # Purely synthetic fixtures; never construed as trading-performance evidence.
    return [
        LabeledMarketExample(
            f"synthetic-{i}", 1000 * (i + 1), 1000 * (i + 1) + 200,
            (1.0 if i % 2 else -1.0, .3 if i % 2 else .1),
            i % 2,
        ) for i in range(count)
    ]


def fixture(symbol="EURUSD", side=EntrySide.BUY, *, ready=True, blackout=False):
    instrument = TradableInstrument(
        11, 1, symbol, symbol, "EUR", "USD", "USD", AssetClass.FOREX,
        True, True, True, ready, True, True,
    )
    proposal = EntryProposal(True, side, EntryMode.TREND_PULLBACK, .91, .09, 2.0, 1.2, 3, ("fixture",))
    news = NewsContext(True, blackout, .10, .20, 2, 2, ("news_context_ready",))
    candidate = MarketCandidate(instrument, proposal, news, .5, .95)
    quality = SetupQualityInput(proposal, .9, .5, 3.0, .95, 1.1, True, blackout, .10, .9, 0.0)
    return candidate, quality


class AIBrainTests(unittest.TestCase):
    def setUp(self):
        self.brain = KatarinaAIBrain()
        self.report = self.brain.train_candidate(examples(), feature_names=("technical", "macro"))

    def signal(self, *, candidate=None, quality=None, regime=None, **kwargs):
        c, q = fixture() if candidate is None else (candidate, quality)
        return self.brain.evaluate(
            c, q, self.report, features=kwargs.pop("features", (1.0, .3)),
            observed_ns=kwargs.pop("observed_ns", 100_000),
            regime=regime or RegimeAssessment(Regime.TREND_UP, .9, False),
            system_healthy=kwargs.pop("system_healthy", True),
            **kwargs,
        )

    def test_chronological_out_of_sample_training(self):
        self.assertTrue(self.report.valid, self.report.reasons)
        self.assertLess(self.report.model_brier, self.report.baseline_brier)
        self.assertGreaterEqual(self.report.train_count, 24)
        self.assertGreaterEqual(self.report.test_count, 12)
        self.assertLess(self.report.trained_until_ns, self.report.cutoff_ns)
        self.assertFalse(self.report.live_risk_ready)
        self.assertEqual(len(self.report.model_hash), 64)

    def test_buy_and_sell_research_only(self):
        buy = self.signal()
        self.assertEqual(buy.action, DecisionAction.BUY)
        self.assertGreater(buy.net_win_probability, .55)
        self.assertFalse(buy.live_risk_authorized)
        self.assertTrue(buy.research_only)
        c, q = fixture(side=EntrySide.SELL)
        sell = self.signal(candidate=c, quality=q)
        self.assertEqual(sell.action, DecisionAction.SELL)
        self.assertLessEqual(sell.risk_multiplier, 1.0)

    def test_negative_model_probability_vetoes_entry(self):
        out = self.signal(features=(-1.0, .1))
        self.assertEqual(out.action, DecisionAction.NO_TRADE)
        self.assertEqual(out.risk_multiplier, 0)

    def test_purge_late_labels_from_training(self):
        data = examples()
        for i in range(12):
            data[i] = replace(data[i], label_known_ns=120_000)
        out = self.brain.train_candidate(data, feature_names=("technical", "macro"))
        self.assertLess(out.train_count, self.report.train_count)
        self.assertLess(out.trained_until_ns, out.cutoff_ns)

    def test_insufficient_data_cold_start(self):
        r = self.brain.train_candidate(examples(8), feature_names=("technical", "macro"))
        self.assertFalse(r.valid)
        self.assertIsNone(r.model)
        self.assertIn("insufficient_labeled_samples", r.reasons)

    def test_single_class_fails_closed(self):
        rows = [replace(x, profitable_after_costs=1) for x in examples()]
        r = self.brain.train_candidate(rows, feature_names=("technical", "macro"))
        self.assertFalse(r.valid)
        self.assertIsNone(r.model)
        self.assertIn("single_class_training", r.reasons)

    def test_no_predictive_signal_when_labels_are_random_vs_features(self):
        rows = [replace(x, profitable_after_costs=(i // 2) % 2) for i, x in enumerate(examples())]
        r = self.brain.train_candidate(rows, feature_names=("technical", "macro"))
        self.assertFalse(r.valid)
        self.assertIsNone(r.model)

    def test_training_rejects_schema_and_duplicates(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.brain.train_candidate([*examples(), examples()[0]], feature_names=("technical", "macro"))
        with self.assertRaisesRegex(ValueError, "feature schema"):
            self.brain.train_candidate(examples(), feature_names=("only_one",))
        with self.assertRaises(ValueError):
            LabeledMarketExample("test", 1, 2, (nan,), 0)
        with self.assertRaises(ValueError):
            LabeledMarketExample("future", 5, 4, (1.0,), 0)

    def test_no_signal_when_market_or_news_not_ready(self):
        c, q = fixture(ready=False)
        self.assertEqual(self.signal(candidate=c, quality=q).action, DecisionAction.NO_TRADE)
        c, q = fixture(blackout=True)
        self.assertEqual(self.signal(candidate=c, quality=q).action, DecisionAction.NO_TRADE)
        self.assertEqual(self.signal(system_healthy=False).action, DecisionAction.SAFE_MODE)

    def test_blocks_inconsistent_news_and_quality(self):
        c, q = fixture()
        tampered = replace(q, news_risk_score=.95)
        self.assertIn("inconsistent_quality_evidence", self.signal(candidate=c, quality=tampered).reasons)

    def test_blocks_ood_regime_drift_features_and_stale_model(self):
        ood = RegimeAssessment(Regime.UNKNOWN, 0.0, True)
        self.assertEqual(self.signal(regime=ood).action, DecisionAction.NO_TRADE)
        self.assertIn("feature_or_outcome_drift", self.signal(drift_detected=True).reasons)
        self.assertIn("feature_out_of_distribution", self.signal(features=(8.0, .3)).reasons)
        self.assertIn("stale_or_noncausal_model", self.signal(observed_ns=self.report.cutoff_ns).reasons)

    def test_quality_veto_and_invalid_report(self):
        c, q = fixture()
        self.assertEqual(self.signal(candidate=c, quality=replace(q, spread_bps=10.0)).action, DecisionAction.NO_TRADE)
        denied = replace(self.report, valid=False, model=None)
        out = self.brain.evaluate(
            c, q, denied, features=(1.0, .3), observed_ns=100_000,
            regime=RegimeAssessment(Regime.TREND_UP, .9, False),
            system_healthy=True,
        )
        self.assertIn("model_not_out_of_sample_validated", out.reasons)

    def test_deterministic_training_and_batch_rank(self):
        repeat = self.brain.train_candidate(list(reversed(examples())), feature_names=("technical", "macro"))
        self.assertEqual(repeat.model_hash, self.report.model_hash)
        s1 = self.signal()
        c, q = fixture("GBPUSD", EntrySide.SELL)
        s2 = self.signal(candidate=c, quality=q)
        no_trade = self.signal(features=(-1.0, .1))
        ranked = self.brain.rank_research([no_trade, s2, s1])
        self.assertEqual([x.symbol for x in ranked], ["EURUSD", "GBPUSD"])
        self.assertTrue(all(x.research_only and not x.live_risk_authorized for x in ranked))


if __name__ == "__main__":
    unittest.main()
