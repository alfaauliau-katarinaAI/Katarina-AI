"""Synthetic fixtures test ingestion safety, not strategy performance."""
import csv
from decimal import Decimal
import importlib.util
from pathlib import Path
import tempfile
import unittest

from katarina.research.mt5_journal import FEATURE_NAMES, NUMERIC, load_journal


class MT5JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'journal.csv'
        self.row = dict.fromkeys(NUMERIC, '1')
        self.row.update(run_tag='fixture', entry_time='2026.09.01 10:34',
                        exit_time='2026.09.01 10:34', side='BUY', net_profit='2.00', win='1')

    def write(self, rows, encoding='utf-8-sig'):
        with self.path.open('w', encoding=encoding, newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.row), delimiter=';')
            writer.writeheader()
            writer.writerows(rows)

    def load(self, count=1, profit='2.00'):
        return load_journal(self.path, expected_trades=count, expected_net_profit=Decimal(profit))

    def test_encodings_and_conservative_minute_interval(self):
        for encoding in ('utf-8-sig', 'utf-16'):
            with self.subTest(encoding=encoding):
                self.write([self.row], encoding)
                data = self.load()
                self.assertEqual(data.rows[0].label_known_ns - data.rows[0].observed_ns, 60_000_000_000)
                self.assertEqual(len(data.rows[0].features), len(FEATURE_NAMES))
                self.assertEqual(len(data.source_sha256), 64)

    def test_sort_keeps_outcomes_aligned(self):
        later = dict(self.row, entry_time='2026.09.02 10:34', exit_time='2026.09.02 10:35',
                     side='SELL', net_profit='-3', win='0')
        self.write([later, self.row])
        data = self.load(2, '-1')
        self.assertEqual(data.sides, ('BUY', 'SELL'))
        self.assertEqual(data.net_profits, (Decimal('2'), Decimal('-3')))

    def test_outcomes_do_not_become_features(self):
        self.write([self.row]); before = self.load().rows[0]
        self.write([dict(self.row, net_profit='-2', win='0', exit_time='2026.09.02 10:34')])
        after = self.load(profit='-2').rows[0]
        self.assertEqual(before.features, after.features)
        self.assertEqual(before.sample_id, after.sample_id)
        self.assertNotEqual(before.profitable_after_costs, after.profitable_after_costs)

    def test_reject_bad_values(self):
        for update in ({'rsi':'NaN'}, {'adx':'101'}, {'atr_pct':'0'}, {'spread_atr':'-1'},
                       {'net_profit':'Infinity'}, {'win':'0'}, {'side':'LONG'},
                       {'exit_time':'2026.08.31 10:34'}, {'entry_time':'garbage'}):
            with self.subTest(update=update):
                self.write([dict(self.row, **update)])
                with self.assertRaises(ValueError): self.load()

    def test_reject_duplicate_trade_and_mixed_runs(self):
        for second in (self.row, dict(self.row, run_tag='other')):
            self.write([self.row, second])
            with self.assertRaises(ValueError): self.load(2, '4')

    def test_reconciliation_required(self):
        self.write([self.row])
        for count, total in ((2, '2'), (1, '1'), (1, 'NaN')):
            with self.assertRaises(ValueError): self.load(count, total)

    def test_reject_missing_duplicate_and_truncated_columns(self):
        self.write([self.row]); original = self.path.read_text(encoding='utf-8-sig')
        for content in (original.replace('rsi;', 'missing;', 1),
                        original.replace('adx;', 'rsi;', 1), original.rsplit(';', 1)[0]):
            self.path.write_text(content)
            with self.assertRaises(ValueError): self.load()

    def test_insufficient_data_does_not_export_model(self):
        source = Path(__file__).resolve().parents[2] / 'scripts/ai/validate_mt5_journal.py'
        spec = importlib.util.spec_from_file_location('journal_cli', source)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.write([self.row])
        result = module.evaluate(self.path, 1, Decimal('2'))
        self.assertEqual(result['result'], 'NO_VALIDATED_AI_CANDIDATE')
        self.assertIsNone(result['validation']['model'])
        self.assertFalse(result['live_execution_enabled'])
        self.assertFalse(result['strategy_validated'])
