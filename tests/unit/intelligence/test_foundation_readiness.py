"""Foundation readiness must never promote research to trading."""
import unittest
from datetime import datetime,timezone
from katarina.intelligence.operations.foundation_readiness import assess_foundation

STAMP=datetime(2026,10,15,5,tzinfo=timezone.utc).isoformat()


def report():
    return {
        "observed_at_utc":STAMP,
        "market_snapshot_tick_utc":"2026-10-15T04:59:59+00:00",
        "time_reference":{
            "canonical_market_clock":"MT5_TICK_SERVER_TIME_CONVERTED_TO_UTC",
            "confirming_symbols":2,"historical_dst_verified":False,
        },
        "symbols":{
            "XAUUSD.vx":{"blocking_reasons":[]},
            "EURUSD.vx":{"blocking_reasons":["no_verified_relevant_news"]},
        },
        "observed_symbols":2,
        "final_actions":{"WAIT":2},
        "news_feed_status":{k:"CACHED" for k in ("fed","ecb","boe","calendar")},
        "broker_account_monitor":{
            "status":"READONLY_ACCOUNT_OBSERVED_NO_RISK_CLEARANCE",
            "connected":True,"algo_trading_off":True,
            "positions_read_success":True,
            "positions_missing_protective_sl":0,
        },
        "broker_history_coverage":{
            "status":"DEAL_FIELDS_OBSERVED_NOT_FULL_RISK_LEDGER",
            "historical_range_complete":False,
            "live_execution_authorized":False,
        },
        "official_cache_integrity":{
            "all_four_cache_digests_fresh":True,
            "policy_inference_from_headlines_authorized":False,
        },
        "unified_cognitive_cycle":{
            "source_snapshot_matches_active":True,
            "real_execution_authorized":False,
            "matured_observations":7,
        },
        "virtual_shadow_summary":{"counts":{"OPEN":1}},
        "orders_submitted":0,
        "live_execution_authorized":False,
        "production_execution":False,
    }


class FoundationReadinessTests(unittest.TestCase):
    def test_healthy_research_is_not_live_ready(self):
        outcome=assess_foundation(report(),expected_symbols=2)
        self.assertEqual(outcome["status"],
                         "RESEARCH_FOUNDATION_PASS_PRODUCTION_BLOCKED")
        self.assertTrue(all(outcome["engineering_checks"].values()))
        self.assertFalse(outcome["live_execution_authorized"])
        self.assertTrue(outcome["unknown_or_unverified_production_gates"])
        self.assertTrue(outcome["news_transport_is_not_verified_trading_news"])

    def test_future_market_tick_and_unknown_clock_degrade(self):
        r=report()
        r["market_snapshot_tick_utc"]="2026-10-15T05:00:04+00:00"
        self.assertFalse(assess_foundation(r,expected_symbols=2)
                         ["engineering_checks"]["canonical_utc_market_clock"])
        r["market_snapshot_tick_utc"]="2026-10-15T04:59:59+00:00"
        r["time_reference"]["canonical_market_clock"]="BROKER_WALL_GUESSED"
        self.assertFalse(assess_foundation(r,expected_symbols=2)
                         ["engineering_checks"]["canonical_utc_market_clock"])

    def test_unverified_memory_and_tampered_shadow_exposure_degrade(self):
        r=report();r["unified_cognitive_cycle"]["source_snapshot_matches_active"]=False
        r["virtual_shadow_summary"]["counts"]["OPEN"]=2
        o=assess_foundation(r,expected_symbols=2)
        self.assertIn("unified_memory_checkpoint_matches",
                      o["engineering_failure_reasons"])
        self.assertIn("single_virtual_portfolio_limit",
                      o["engineering_failure_reasons"])

    def test_missing_quotes_and_active_trading_never_pass(self):
        r=report()
        r["broker_account_monitor"]["algo_trading_off"]=False
        r["symbols"]["XAUUSD.vx"]["blocking_reasons"]=["sensor_error:ValueError"]
        o=assess_foundation(r,expected_symbols=2)
        self.assertIn("read_only_terminal_confirmed",o["engineering_failure_reasons"])
        self.assertIn("sensors_without_errors",o["engineering_failure_reasons"])

    def test_unprotected_position_degrades_even_in_readonly(self):
        r=report()
        r["broker_account_monitor"]["positions_missing_protective_sl"]=1
        o=assess_foundation(r,expected_symbols=2)
        self.assertIn("no_unprotected_broker_positions",
                      o["engineering_failure_reasons"])
        self.assertFalse(o["live_execution_authorized"])

    def test_unverified_news_transport_degrades_not_fabricated_ready(self):
        r=report();r["news_feed_status"]["fed"]="ERROR"
        o=assess_foundation(r,expected_symbols=2)
        self.assertFalse(o["engineering_checks"]["official_news_cache_transport_reachable"])
        self.assertFalse(o["live_execution_authorized"])

    def test_cached_error_and_deals_not_readable_degrade(self):
        r=report()
        r["broker_history_coverage"]["status"]="HISTORICAL_DEALS_UNAVAILABLE"
        r["official_cache_integrity"]["all_four_cache_digests_fresh"]=False
        x=assess_foundation(r,expected_symbols=2)
        self.assertIn("recent_broker_deal_book_readable",
                      x["engineering_failure_reasons"])
        self.assertIn("official_source_cache_digest_and_freshness",
                      x["engineering_failure_reasons"])
        self.assertFalse(x["live_execution_authorized"])

    def test_invalid_expected_symbols_rejected(self):
        for n in (0,18,True,-1):
            with self.assertRaises(ValueError):
                assess_foundation(report(),expected_symbols=n)
