"""Fail-closed, hash-grounded tests for the frozen P9 V2/V3 hybrid (no orders)."""
import gzip
import hashlib
import json
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/"research"/"p9_v2_v31_hybrid"
MANIFEST=DIR/"HYBRID_BALANCED_ADR_FROZEN_20261119.json"

class TestP9V2V31HybridFrozenResearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info=json.loads(MANIFEST.read_text(encoding="utf8"))

    def test_research_only_and_no_order_authority(self):
        d=self.info
        self.assertTrue(d["research_only"])
        self.assertTrue(d["code_non_executable"])
        self.assertEqual(d["status"],"FROZEN_RESEARCH_CHALLENGER_NOT_PROMOTED")
        a=d["authorization"]
        self.assertFalse(a["live_authorized"])
        self.assertFalse(a["demo_authorized"])
        self.assertFalse(a["can_send_orders"])
        self.assertFalse(a["order_execution_authorized"])
        self.assertFalse(a["production_changes_allowed"])
        self.assertEqual(a["authorized_risk_pct"],0.0)
        self.assertEqual(a["evidence_risk_gate"],"WAIT")

    def test_exact_engine_selection_and_no_extra_sell(self):
        m=self.info["engine_map"]
        self.assertEqual(m["XAUUSD_H1_BUY"],"V3_GROWTH_DEFENSIVE_DONCHIAN48")
        self.assertEqual(m["XAUUSD_H4_BUY"],"V2_KELTNER")
        self.assertEqual(m["NAS100_H4_SELL"],"V3_GROWTH_DEFENSIVE_MACD_ZERO")
        self.assertEqual(m["EURJPY_H4_BUY"],"SHARED_MOMENTUM24")
        self.assertEqual(m["USDCHF_H4_BUY"],"SHARED_RSI_REENTRY")
        self.assertEqual(m["USDCHF_H4_SELL"],"V3_MACD_ZERO_GATED_BY_PREVIOUS_DAY_ADR_RATIO")
        self.assertEqual(m["EURJPY_H1_SELL"],"DISABLED")
        self.assertEqual(m["XAUUSD_H1_SELL"],"DISABLED")
        self.assertEqual(m["NAS100_BUY"],"DISABLED")

    def test_previous_completed_days_and_exact_adr_thresholds(self):
        gate=self.info["usdchf_sell_conditional"]
        self.assertEqual(gate["source"],"PREVIOUS_FULLY_COMPLETED_BROKER_TRADING_DAYS_ONLY")
        self.assertGreaterEqual(gate["min_full_days"],100)
        self.assertEqual(gate["eligible_candidate_signals_in_27_months"],12)
        self.assertEqual(gate["measure"],"ADR20_OVER_ADR100")
        def should_consider(previous_completed_day_ratio):
            return gate["lower_inclusive"]<=previous_completed_day_ratio<gate["upper_exclusive"]
        self.assertFalse(should_consider(.79999))
        self.assertTrue(should_consider(.8))
        self.assertTrue(should_consider(1.199))
        self.assertFalse(should_consider(1.2))

    def test_all_archived_evidence_hashes_and_uncompressed_hashes(self):
        bundle=self.info["repo_evidence_files"]
        self.assertEqual(len(bundle),8)
        for path,record in bundle.items():
            with self.subTest(path=path):
                p=DIR/path
                self.assertTrue(p.is_file())
                raw=p.read_bytes()
                self.assertEqual(
                    hashlib.sha256(raw.replace(b"\r\n",b"\n")).hexdigest(),
                    record["normalized_lf_sha256"],
                )
                self.assertEqual(
                    len(raw.replace(b"\r\n",b"\n")),
                    record["normalized_lf_size"],
                )
                decoded=gzip.decompress(raw) if record["gzip"] else raw
                # Git checkout may convert EOLs for text sources on Windows;
                # normalized content must remain exactly the frozen source.
                source=(DIR/path).read_bytes()
                self.assertEqual(
                    hashlib.sha256(source.replace(b"\r\n",b"\n")).hexdigest(),
                    record["normalized_lf_sha256"],
                )
                if record["gzip"]:
                    self.assertEqual(hashlib.sha256(decoded).hexdigest(),record["source_sha256"])
                    self.assertEqual(len(decoded),record["source_size"])
        for sha in self.info["source_sha256_on_vps"].values():
            self.assertRegex(sha,r"^[0-9a-f]{64}$")

    def test_cost_stress_benchmarks_and_guard_failure(self):
        h=self.info["historical"]
        self.assertEqual(h["variants_tested"],1184)
        self.assertEqual(h["months"],27)
        self.assertTrue(h["source_is_broker_h1h4_ohlc_not_native_realtick"])
        self.assertTrue(h["2026_already_seen_not_holdout"])
        self.assertEqual(h["hybrid_normal_usd_per_month"],1349.21)
        self.assertEqual(h["hybrid_stress_minus06r_usd_per_month"],121.78)
        self.assertGreater(h["hybrid_stress_minus07r_closed_dd_pct"],8)
        self.assertGreater(h["hybrid_stress_minus07r_dd_veto"],0)
        self.assertGreater(h["risk_research_base_pct"] if "risk_research_base_pct" in h else self.info["risk_research_only"]["base_pct_by_family"]["NAS"],
                           self.info["authorization"]["native_cap_research_reference_pct"])

    def test_forward_and_readiness_unverified(self):
        f=self.info["forward_test"]
        self.assertEqual(f["status"],"NOT_STARTED_NO_INDEPENDENT_FORWARD_OUTCOMES")
        self.assertTrue(f["do_not_refit_on_holdout"])
        self.assertTrue(f["official_stage0_not_forward_performance_evidence"])
        self.assertLessEqual(datetime.fromisoformat(f["not_before_frozen_at_utc"]),datetime.now(timezone.utc))
        x=self.info["readiness"]
        self.assertEqual(x["stage0"],"IN_PROGRESS")
        self.assertTrue(x["EURJPY_broker_symbol_available"])
        self.assertTrue(x["USDCHF_broker_symbol_available"])
        self.assertFalse(x["real_tick_27_month_native_tester_completed"])
        self.assertFalse(x["broker_costs_independently_verified"])
        self.assertFalse(x["floating_equity_dd_verified"])
        self.assertFalse(x["external_model_review_pass"])

if __name__=="__main__":
    unittest.main()
