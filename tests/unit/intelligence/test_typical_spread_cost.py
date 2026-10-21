"""Research cost uses the typical broker spread, not one rollover quote."""
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from katarina.intelligence.lab.autonomous_research import GRID, ResearchWorker
from katarina.intelligence.lab.continuous_research_lab import (
    MAX_SPREAD_TO_RANGE, cost_gate, select_batch, setup, step, typical_spread)
from katarina.monitoring.activity_trace import ActivityTrace


def rates(n=600, spread_points=20, rollover_points=600):
    """H1 bars with a 2.0 price range; every 24th bar is a wide-spread rollover hour."""
    out = []
    for i in range(n):
        base = 100 + i * .01
        out.append(dict(time=100000 + i * 3600, open=base, high=base + 1, low=base - 1, close=base + .01,
                        spread=rollover_points if i % 24 == 0 else spread_points))
    return out


class Broker:
    TIMEFRAME_H1 = 60

    def __init__(self, quote_spread=.6, point=.001, spread_points=20, bars=None):
        self.quote_spread, self.point, self.spread_points = quote_spread, point, spread_points
        self.bars = bars

    def symbol_select(self, *args):
        return True

    def symbol_info(self, symbol):
        return SimpleNamespace(point=self.point)

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=100, ask=100 + self.quote_spread)

    def copy_rates_from_pos(self, symbol, frame, offset, count):
        return self.bars if self.bars is not None else rates(spread_points=self.spread_points)


class TypicalSpreadTests(unittest.TestCase):
    def test_median_bar_spread_ignores_rollover_and_live_quote(self):
        # Typical 20 points * 0.001 = 0.02; rollover hours (600 points) and a 0.6
        # live quote (as captured during rollover) must not set the cost.
        cost = typical_spread(Broker(quote_spread=.6), 'XAUUSD', rates())
        self.assertEqual(cost['source'], 'MEDIAN_H1_BAR_SPREAD')
        self.assertAlmostEqual(cost['price'], .02)
        self.assertEqual(cost['samples'], 600)
        self.assertAlmostEqual(cost['current_quote'], .6)

    def test_falls_back_to_quote_without_bar_spreads(self):
        bars = [{k: v for k, v in r.items() if k != 'spread'} for r in rates()]
        cost = typical_spread(Broker(quote_spread=.05), 'X', bars)
        self.assertEqual(cost['source'], 'CURRENT_QUOTE_FALLBACK')
        self.assertAlmostEqual(cost['price'], .05)
        too_few = rates(n=50)
        self.assertEqual(typical_spread(Broker(quote_spread=.05), 'X', too_few)['source'], 'CURRENT_QUOTE_FALLBACK')

    def test_no_cost_evidence_returns_none(self):
        broker = Broker()
        broker.symbol_info_tick = lambda symbol: None
        self.assertIsNone(typical_spread(broker, 'X', [{'time': 1}]))

    def test_cost_gate_uses_median_range(self):
        rows = [(i * 3600, 100, 101, 99, 100) for i in range(600)]  # range 2.0
        ratio, prohibitive = cost_gate(rows, .02)
        self.assertAlmostEqual(ratio, .01)
        self.assertFalse(prohibitive)
        ratio, prohibitive = cost_gate(rows, 2 * MAX_SPREAD_TO_RANGE + .01)
        self.assertTrue(prohibitive)


class LabAndWorkerTests(unittest.TestCase):
    def run_lab(self, broker):
        with closing(sqlite3.connect(':memory:')) as db:
            now = datetime.now(timezone.utc)
            select_batch(db, [SimpleNamespace(name='TEST', trade_mode=4)], 17, now)
            with tempfile.TemporaryDirectory() as root:
                step(db, broker, root, now)
            run = json.loads(db.execute('SELECT result_json FROM lab_runs').fetchone()[0])
            status = db.execute("SELECT status FROM lab_universe WHERE symbol='TEST'").fetchone()[0]
        return run, status

    def test_lab_records_typical_spread_and_source(self):
        run, status = self.run_lab(Broker(quote_spread=.6))
        self.assertEqual(run['version'], 'broker-lab-v3')
        self.assertEqual(run['spread_source'], 'MEDIAN_H1_BAR_SPREAD')
        self.assertAlmostEqual(run['spread_proxy_price'], .02)
        self.assertAlmostEqual(run['current_quote_spread'], .6)
        self.assertAlmostEqual(run['spread_to_median_range'], .01)
        self.assertFalse(run['cost_prohibitive'])
        self.assertEqual(status, 'EXPLORATORY_ONLY')

    def test_lab_marks_wide_typical_spread_cost_prohibitive(self):
        run, status = self.run_lab(Broker(spread_points=600))  # 0.6 of a 2.0 range
        self.assertTrue(run['cost_prohibitive'])
        self.assertEqual(status, 'COST_PROHIBITIVE')

    def test_worker_skips_cost_prohibitive_and_tags_spread_source(self):
        rows = [(3600 * i, 100 + i * .1, 101 + i * .1, 99 + i * .1, 100.2 + i * .1) for i in range(700)]
        for prohibitive, expected in ((True, 0), (False, 1)):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with closing(sqlite3.connect(root / 'context.sqlite3')) as db, db:
                    setup(db)
                    db.execute("INSERT INTO lab_universe(symbol) VALUES('FIXTURE')")
                    db.executemany('INSERT INTO lab_bars VALUES(?,?,?,?,?,?)', [('FIXTURE', *r) for r in rows])
                    db.execute('INSERT INTO lab_runs VALUES(?,?,?,?,?)', ('src', 'FIXTURE', '2026-01-01', 'x', json.dumps(
                        {'spread_proxy_price': .01, 'spread_source': 'MEDIAN_H1_BAR_SPREAD', 'cost_prohibitive': prohibitive})))
                with patch('katarina.intelligence.lab.autonomous_research.GRID', GRID[:1]), \
                        patch('katarina.intelligence.lab.research_capacity.research_capacity', return_value={'status': 'READY'}):
                    ResearchWorker(root, ActivityTrace(root)).tick()
                with closing(sqlite3.connect(root / 'experiment-jobs.sqlite3')) as db:
                    trials = db.execute('SELECT result_json FROM trials').fetchall()
                self.assertEqual(len(trials), expected)
                if trials:
                    self.assertEqual(json.loads(trials[0][0])['spread_source'], 'MEDIAN_H1_BAR_SPREAD')


if __name__ == '__main__':
    unittest.main()
