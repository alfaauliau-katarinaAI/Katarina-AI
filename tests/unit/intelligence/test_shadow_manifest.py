import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from katarina.intelligence.shadow_manifest import (
    ShadowStudyIdentity,verify_or_create_manifest,broker_fingerprint,config_sha256
)


def ident():
    return ShadowStudyIdentity(
        strategy_version="GOLD_SHADOW_V1",
        frozen_at_utc="2026-10-11T00:00:00+00:00",
        symbol="XAUUSD.vx",account_currency="USD",
        broker_account_fingerprint=broker_fingerprint(
            server="research-broker",login=123,currency="USD"),
        initial_paper_balance_native=1000.,
        risk_config_sha256="f"*64,commission_per_lot_assumed=None)


class ShadowManifestTests(unittest.TestCase):
    def test_restart_preserves_virtual_capital_and_setup_config(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertTrue(verify_or_create_manifest(root,ident()))
            self.assertFalse(verify_or_create_manifest(root,ident()))
            self.assertTrue((Path(root)/"manifest.json").exists())

    def test_freeze_currency_risk_config_and_capital_cannot_change_in_place(self):
        with tempfile.TemporaryDirectory() as root:
            v=ident()
            verify_or_create_manifest(root,v)
            for x in (
                replace(v,strategy_version="v2"),
                replace(v,initial_paper_balance_native=10000.),
                replace(v,account_currency="USC"),
                replace(v,risk_config_sha256="0"*64),
                replace(v,broker_account_fingerprint="1"*64),
                replace(v,commission_per_lot_assumed=10.),
            ):
                with self.subTest(x=x):
                    with self.assertRaisesRegex(ValueError,"shadow_study_identity_mismatch"):
                        verify_or_create_manifest(root,x)

    def test_tampered_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            verify_or_create_manifest(root,ident())
            path=Path(root)/"manifest.json"
            path.write_text("INVALID JSON")
            with self.assertRaisesRegex(ValueError,"corrupt_study_manifest"):
                verify_or_create_manifest(root,ident())

    def test_unknown_account_fingerprint_and_nonfinite_money_rejected(self):
        with self.assertRaisesRegex(ValueError,"unverified_broker_account_identity"):
            broker_fingerprint(server="",login=123,currency="USD")
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,"invalid_shadow_study_identity"):
                verify_or_create_manifest(root,replace(
                    ident(),initial_paper_balance_native=float("inf")))

    def test_config_sha_reacts_to_policy_changes(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"risk.json"
            path.write_text('{"max_risk":0.01}')
            first=config_sha256(path)
            path.write_text('{"max_risk":0.02}')
            self.assertNotEqual(first,config_sha256(path))


if __name__=="__main__":
    unittest.main()
