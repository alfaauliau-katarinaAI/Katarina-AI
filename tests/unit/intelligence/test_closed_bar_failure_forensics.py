"""Frozen signal root cause accounting and full two-hour expiry safeguards."""
import unittest
from datetime import datetime,timedelta,timezone

from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle
from katarina.intelligence.lab.causal_market_replay import simulate_ohlc_proxy
from katarina.intelligence.lab.closed_bar_failure_forensics import (
    diagnose_frozen_replay,
)

NOW=datetime(2026,9,24,0,tzinfo=timezone.utc)


def candles(count=25,*,ambiguous=False):
    out=[]
    for i in range(count):
        high=105. if ambiguous and i==1 else 101.
        low=95. if ambiguous and i==1 else 99.
        out.append(SensorCandle(NOW+timedelta(minutes=5*i),
            100.,high,low,100.))
    return tuple(out)


def label(reason="STOP_FIRST_BID_OHLC_PROXY"):
    t=int(NOW.timestamp())
    return {
        "symbol":"XAUUSD.vx","method":"TREND_PULLBACK",
        "side":"BUY","regime":"TREND_UP",
        "signal_at":t,"label_known_at":t+300,
        "proxy_exit_reason":reason,
        "proxy_gross_r":-1.,"sl":97.,"tp":104.,
        "observed_spread_price":.1,"m15_atr_price":2.,
        "directional_alignment":"THREE_TIMEFRAME_AGREEMENT",
    }


class TestClosedBarFailureForensics(unittest.TestCase):
    def test_incomplete_two_hour_path_is_censored_not_early_time_exit(self):
        self.assertIsNone(simulate_ohlc_proxy(
            candles(7),0,"BUY",97.,104.,.1))
        expiry=simulate_ohlc_proxy(candles(25),0,"BUY",97.,104.,.1)
        self.assertIsNotNone(expiry)
        self.assertEqual(expiry[2],"TIMESTOP_OHLC_PROXY")
        self.assertEqual(expiry[1],int((NOW+timedelta(hours=2)).timestamp()))

    def test_legitimate_early_stop_can_close_without_full_horizon(self):
        event=simulate_ohlc_proxy(candles(2,ambiguous=True),
                                  0,"BUY",97.,104.,.1)
        self.assertEqual(event[2],"STOP_FIRST_BID_OHLC_PROXY")
        self.assertLess(event[0],0)

    def test_intrabar_both_stop_and_target_recorded_not_winner(self):
        full=candles(5,ambiguous=True)
        events=[label()]
        doc=diagnose_frozen_replay({
            "signals":events,
            "all_technical_proposals":[{"id":"historically_frozen"}],
            "counters":{"evaluated":4,"proxy_completed":1,
                "quote_path_unavailable":1,"technical_wait":1,
                "invalid_rr_or_stop":1,"spread_unavailable":0}
        },{"XAUUSD.vx":{"M5":full}})
        self.assertEqual(doc["totals"]["n"],1)
        self.assertEqual(doc["totals"]["loss_exit_causes"]["STOP"],1)
        self.assertEqual(doc["totals"]["ambiguous_intrabar_stop_vs_target_count"],1)
        self.assertEqual(doc["totals"]["early_stop_within_15m_count"],1)
        self.assertEqual(doc["totals"]["censored_or_gap_proxy_labels"],1)
        self.assertAlmostEqual(doc["totals"]["median_pre_entry_spread_to_risk"],
                               .1/3.1,places=5)
        self.assertFalse(doc["live_execution_authorized"])
        self.assertEqual(len(doc["all_candidate_records"]),1)

    def test_favorable_tp_claim_contradicted_by_same_bar_stop_fails(self):
        with self.assertRaisesRegex(ValueError,"target_label"):
            diagnose_frozen_replay({
                "signals":[label("TARGET_BID_OHLC_PROXY")],
                "all_technical_proposals":[{}],"counters":{}
            },{"XAUUSD.vx":{"M5":candles(5,ambiguous=True)}})

    def test_duplicate_broker_closed_bar_timestamp_rejected(self):
        same=candles(3)
        with self.assertRaisesRegex(ValueError,"duplicate_hist_time"):
            diagnose_frozen_replay({
                "signals":[label()],"all_technical_proposals":[],
                "counters":{}
            },{"XAUUSD.vx":{"M5":(same[0],same[0],same[2])}})


if __name__=="__main__":unittest.main()
