"""WP12: quarantine legacy MT5 acquisition, preserving offline research; no orders."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import Mock, patch

from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle, MarketDecisionPipeline
from katarina.intelligence.perception import screening

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


class LegacyClockTests(unittest.TestCase):
    def test_screening_refuses_unverified_history_before_any_broker_access(self):
        broker = Mock()
        broker.initialize.return_value = False
        with self.assertRaisesRegex(RuntimeError, '^BROKER_BAR_CLOCK_NOT_VERIFIED_WP12$'):
            screening.collect(broker, 'unused-research-terminal')
        self.assertEqual(broker.mock_calls, [])

    def test_legacy_decisions_remain_wait_even_with_fresh_quotes_and_bars(self):
        for shift in (None, 2, 3):
            with self.subTest(shift=shift):
                mt5 = ModuleType('MetaTrader5')
                mt5.initialize = Mock(return_value=True)
                mt5.shutdown = Mock()
                epoch = NOW.timestamp() + (shift or 0) * 3600
                mt5.symbol_info_tick = Mock(return_value=SimpleNamespace(
                    time=epoch, time_msc=epoch * 1000, bid=100., ask=100.01))
                mt5.symbol_info = Mock(return_value=SimpleNamespace(point=.01))
                mt5.order_send = Mock(side_effect=AssertionError('no orders'))
                smoke = ModuleType('smoke_closed_market_decision')
                smoke.SYMBOLS = ('EURUSD', 'GBPUSD', 'USDJPY')
                smoke.TFS = {name: (minutes, minutes) for name, minutes in
                             (('M5', 5), ('M15', 15), ('H1', 60))}
                bars = {name: [SensorCandle(NOW - timedelta(minutes=minutes * (69-i)),
                            100+i*.1, 101+i*.1, 99+i*.1, 100.5+i*.1, 100)
                            for i in range(70)] for name, (_, minutes) in smoke.TFS.items()}
                smoke.candles_for = Mock(return_value=bars)
                spec = importlib.util.spec_from_file_location(
                    'wp12_legacy_decisions', ROOT/'scripts/ai/run_readonly_decisions.py')
                module = importlib.util.module_from_spec(spec)
                with patch.dict('sys.modules', {'MetaTrader5': mt5, 'smoke_closed_market_decision': smoke}):
                    spec.loader.exec_module(module)
                pipeline = MarketDecisionPipeline()
                with patch.object(module, 'datetime', FixedDatetime), \
                     patch.object(module, 'infer_clock_shift', return_value=SimpleNamespace(
                         observed_hours_shift=shift, suitable_for_readonly_snapshot=shift is not None)), \
                     patch.object(module, 'MarketDecisionPipeline', return_value=pipeline), \
                     patch.object(pipeline, 'evaluate', wraps=pipeline.evaluate) as evaluate, \
                     patch.object(module, 'publish') as publish, redirect_stdout(io.StringIO()):
                    self.assertEqual(module.main(), 0)
                report = publish.call_args.args[0]
                self.assertEqual(report['symbols_failed'], 0)
                self.assertEqual(evaluate.call_count, 3)
                for call in evaluate.call_args_list:
                    self.assertFalse(call.kwargs['broker_session_open'])
                for row in report['symbols'].values():
                    self.assertEqual(row['action'], 'WAIT')
                    self.assertTrue(row['market_data_fresh'])
                    self.assertFalse(row['bar_history_clock_verified'])
                    self.assertFalse(row['live_execution_authorized'])
                    self.assertEqual(row['quote_fresh'], shift is not None)
                    self.assertEqual(row['broker_clock_verified_current_only'], shift is not None)
                mt5.order_send.assert_not_called()
                mt5.shutdown.assert_called_once_with()
