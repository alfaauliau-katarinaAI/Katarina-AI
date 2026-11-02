import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.research.replay_technical_signals import replay_dataset, to_sensor_candle


class ReplayTechnicalSignalsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _build_synthetic_dataset(self, symbol="EURUSD", n_bars=30):
        base = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        m5 = []
        for i in range(n_bars):
            opened = base + timedelta(minutes=i * 5)
            closed = opened + timedelta(minutes=5)
            m5.append({
                "time_utc": opened.isoformat(),
                "open": 1.0500 + i * 0.0001,
                "high": 1.0510 + i * 0.0001,
                "low": 1.0490 + i * 0.0001,
                "close": 1.0505 + i * 0.0001,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
                "closed_at_utc": closed.isoformat(),
            })

        m15 = []
        for i in range(n_bars // 3):
            opened = base + timedelta(minutes=i * 15)
            closed = opened + timedelta(minutes=15)
            m15.append({
                "time_utc": opened.isoformat(),
                "open": 1.0500 + i * 0.0003,
                "high": 1.0520 + i * 0.0003,
                "low": 1.0490 + i * 0.0003,
                "close": 1.0515 + i * 0.0003,
                "tick_volume": 300,
                "spread": 10,
                "real_volume": 0,
                "closed_at_utc": closed.isoformat(),
            })

        h1 = []
        for i in range(max(1, n_bars // 12)):
            opened = base + timedelta(hours=i)
            closed = opened + timedelta(hours=1)
            h1.append({
                "time_utc": opened.isoformat(),
                "open": 1.0500,
                "high": 1.0550,
                "low": 1.0480,
                "close": 1.0530,
                "tick_volume": 1200,
                "spread": 10,
                "real_volume": 0,
                "closed_at_utc": closed.isoformat(),
            })

        h4 = []
        for i in range(max(1, n_bars // 48)):
            opened = base + timedelta(hours=i * 4)
            closed = opened + timedelta(hours=4)
            h4.append({
                "time_utc": opened.isoformat(),
                "open": 1.0500,
                "high": 1.0600,
                "low": 1.0450,
                "close": 1.0550,
                "tick_volume": 4800,
                "spread": 10,
                "real_volume": 0,
                "closed_at_utc": closed.isoformat(),
            })

        return {
            symbol: {
                "M5": m5,
                "M15": m15,
                "H1": h1,
                "H4": h4,
            }
        }

    def test_replay_tallies_signals_with_zero_orders(self):
        dataset = self._build_synthetic_dataset("EURUSD", n_bars=30)
        result = replay_dataset(dataset, min_m5_bars=20, step_bars=1)

        self.assertEqual(result["orders_submitted"], 0)
        self.assertFalse(result["live_execution_authorized"])
        self.assertEqual(result["total_evaluations"], 11)  # indices 19..29 = 11 steps
        self.assertIn("WAIT", result["signals"])
        self.assertIn("EURUSD", result["by_symbol"])
        self.assertEqual(result["by_symbol"]["EURUSD"]["total"], 11)

    def test_no_future_candle_lookahead(self):
        """Altering candles after the evaluation point must not alter past evaluations."""
        dataset_normal = self._build_synthetic_dataset("EURUSD", n_bars=30)
        dataset_altered = self._build_synthetic_dataset("EURUSD", n_bars=30)

        # Alter bars starting from index 25
        for i in range(25, 30):
            dataset_altered["EURUSD"]["M5"][i]["close"] = 99.9999

        # Run replay up to index 24 (min_m5_bars=20, step=1, total 5 evaluations: 19..23)
        res1 = replay_dataset({"EURUSD": {k: v[:24] if k == "M5" else v for k, v in dataset_normal["EURUSD"].items()}})
        res2 = replay_dataset({"EURUSD": {k: v[:24] if k == "M5" else v for k, v in dataset_altered["EURUSD"].items()}})

        self.assertEqual(res1["signals"], res2["signals"])
        self.assertEqual(res1["by_regime"], res2["by_regime"])


if __name__ == "__main__":
    unittest.main()
