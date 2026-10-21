"""Observer coupling and tamper tests for the new regime layer."""
import unittest
from datetime import datetime,timezone
from katarina.intelligence.multi_market_brain import features,screen
from tests.unit.intelligence.test_market_regime_intelligence import fixture
from backtest_market_regime_labels import groups
from audit_market_regime_labels import audit
NOW=datetime(2026,10,9,12,tzinfo=timezone.utc)

class ClearContext:
    def assess(self,currencies,now):
        return dict(ready=True,reasons=[])

class RegimeObserverTests(unittest.TestCase):
    def _row(self):
        m1=fixture("UP",60,120)
        m5=fixture("UP",300)
        m15=fixture("UP",900)
        h1=fixture("UP",3600)
        return dict(symbol="NAS100.vx",base="USD",profit="USD",
            trade_mode=4,connected=True,tick_time=NOW.timestamp(),
            bid=128.,ask=128.1,point=.1,tick_size=.1,stop_level_points=30,
            errors=[],m1_bars=m1,m5_bars=m5,
            m15_bars=m15,h1_bars=h1,
            m1=features(m1,60,NOW),m5=features(m5,300,NOW))

    def test_existing_observer_emits_parallel_regime_only(self):
        info=screen([self._row()],ClearContext(),NOW)
        market=info["symbols"][0]
        self.assertEqual(market["market_regime_v1"]["regime"],
                         "CONTINUATION_UP")
        self.assertFalse(market["market_regime_v1"]["entry_authorized"])
        self.assertFalse(info["live_execution_enabled"])
        self.assertEqual(info["decision"],"NO_TRADE")

    def test_unregistered_market_does_not_reuse_NAS_profile(self):
        row=self._row()
        row["symbol"]="UNREGISTERED.vx"
        res=screen([row],ClearContext(),NOW)
        self.assertNotIn("market_regime_v1",res["symbols"][0])
        self.assertEqual(res["shadow_candidate_count"],0)

    def test_regime_missing_bars_is_unknown(self):
        row=self._row()
        row.pop("h1_bars")
        info=screen([row],ClearContext(),NOW)
        self.assertEqual(info["symbols"][0]["market_regime_v1"]["regime"],
                         "UNKNOWN")

    def _archive(self):
        event=dict(symbol="NAS100.vx",study_period="october_diagnostic",
            close_time_utc="2026-10-05T12:00:00+00:00",
            regime="CONTINUATION_UP",direction="UP",
            reason_codes=[],evidence_score_0_100=65,
            evidence_is_profit_probability=False,promoted_to_live=False,
            frames={"M5":dict(adx14=35,efficiency=.55,close_age_seconds=0)},
            future_close_displacement={
              "1h":dict(close_time_utc="2026-10-05T13:00:00+00:00",
                signed_directional_displacement_ATR=.7,
                absolute_displacement_ATR=.7,aligned_with_state=True,
                is_transaction_profit=False),
              "4h":None})
        return dict(kind="causal_mtf_market_regime_diagnostics_v1",
            live_execution_enabled=False,model_promotion_allowed=False,
            decision="NO_TRADE",periods_utc=[["october_diagnostic",
                 "2026-10-01","2026-10-10"]],
            trials_count=1,classified_observations=[event],
            by_symbol_regime_period=groups([event]))

    def test_valid_regime_diagnostic_archive_audits(self):
        d=self._archive()
        self.assertEqual(audit(d)["observations_verified"],1)

    def test_regime_diagnostic_forged_future_is_rejected(self):
        d=self._archive()
        d["classified_observations"][0]["future_close_displacement"]["1h"][
           "close_time_utc"]="2026-10-05T11:00:00+00:00"
        with self.assertRaisesRegex(ValueError,"future_clock_wrong"):
            audit(d)

    def test_false_probability_or_trading_claim_is_rejected(self):
        d=self._archive()
        d["classified_observations"][0]["evidence_is_profit_probability"]=True
        with self.assertRaisesRegex(ValueError,"calibration_false_claim"):
            audit(d)
        d=self._archive()
        d["live_execution_enabled"]=True
        with self.assertRaisesRegex(ValueError,"trade_authorization_mutated"):
            audit(d)

if __name__=="__main__":
    unittest.main()
