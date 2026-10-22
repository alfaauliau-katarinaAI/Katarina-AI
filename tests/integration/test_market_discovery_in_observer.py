"""Opt-in market discovery shares the existing observer and never sends orders."""
from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from katarina.adapters.automatic_connection import BoundLocalBroker
from katarina.intelligence.cognition.continuous_observation import run_continuous
from tests.integration.test_automatic_connection import AccountBroker, config


class MarketDiscoveryIntegrationTests(unittest.TestCase):
    def test_opt_in_keeps_canonical_observer_and_live_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            broker = AccountBroker()
            root = Path(tmp)
            with patch.dict(os.environ, {
                "KATARINA_DISCOVER_ALL_BROKER_MARKETS": "1",
            }):
                result = run_continuous(
                    root, config=config(priority=("local",), attempts=1),
                    factories={"local": lambda c: BoundLocalBroker(broker, c)},
                    max_symbols=3, max_cycles=1, fetch_news=False,
                )
            report = json.loads((root / "latest.json").read_text(
                encoding="utf-8"))
            discovery = report["broker_market_discovery"]
            self.assertIn(discovery["status"], (
                "EXPLORATORY_NO_TRADING_AUTHORITY",
                "NO_TRADE_ENABLED_MARKETS",
            ))
            self.assertEqual(result["orders_submitted"], 0)
            self.assertFalse(result["live_execution_authorized"])
            self.assertEqual(report["orders_submitted"], 0)
            self.assertEqual(discovery["orders_submitted"], 0)
            self.assertEqual(broker.orders, 0)
            self.assertEqual(len(report["symbols"]), 3)


if __name__ == "__main__":
    unittest.main()
