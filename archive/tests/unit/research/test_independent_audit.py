from dataclasses import replace
from decimal import Decimal
import unittest

from katarina.intelligence.brain import LabeledMarketExample
from katarina.research.mt5_journal import JournalDataset, FEATURE_NAMES
from katarina.research.independent_audit import audit, profit_summary


def fixture():
    rows = tuple(LabeledMarketExample(str(i), (i+1)*100, (i+1)*100+1,
                 (float(i % 2),)*len(FEATURE_NAMES), i % 2) for i in range(200))
    return JournalDataset(rows, tuple(Decimal(2 if i % 2 else -1) for i in range(200)),
                          ('BUY',)*200, 'fixture')


class IndependentAuditTests(unittest.TestCase):
    def test_final_labels_cannot_change_selected_model(self):
        data = fixture()
        before = audit(data)
        rows = tuple(replace(r, profitable_after_costs=1-r.profitable_after_costs)
                     if i >= 160 else r for i, r in enumerate(data.rows))
        after = audit(replace(data, rows=rows,
                      net_profits=tuple(-p if i >= 160 else p for i, p in enumerate(data.net_profits))))
        self.assertEqual(before['selection'], after['selection'])
        self.assertEqual(before['result'], 'PASS_RESEARCH_FINAL_AUDIT')
        self.assertEqual(after['result'], 'FINAL_AUDIT_REJECTED')
        self.assertFalse(before['strategy_validated'])
        self.assertFalse(before['live_execution_enabled'])

    def test_crossing_labels_purged_before_selection(self):
        data = fixture()
        rows = tuple(replace(r, label_known_ns=20001) if 140 <= i < 160 else r
                     for i, r in enumerate(data.rows))
        result = audit(replace(data, rows=rows))
        self.assertEqual(result['development_count'], 140)
        self.assertLess(result['selection']['trained_until_ns'], result['final_cutoff_ns'])

    def test_empty_and_unsorted_rejected(self):
        data = fixture()
        for broken in (replace(data, rows=()), replace(data, rows=data.rows[::-1])):
            with self.assertRaises(ValueError): audit(broken)

    def test_no_losses_is_not_infinite_profit_factor(self):
        self.assertIsNone(profit_summary([Decimal(1)])['profit_factor'])
        self.assertIsNone(profit_summary([])['win_rate'])
