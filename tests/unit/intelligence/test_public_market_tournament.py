"""Public-data strategy tournament functional and leakage safeguards.

Network mocked in tests; data-dependent job separately downloads genuine
public BID/ASK candles from Dukascopy.
"""
from __future__ import annotations
from datetime import date
import lzma
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from public_market_tournament import (
    QuoteCandle, aggregate, calculate_fill, parse_minute_file, load_public_minutes,
    run, metrics, RECORD)
from katarina.intelligence.adaptive_strategy_library import StrategyHypothesis


def q(time,*,bid_open=100.,bid_high=101.,bid_low=99.,bid_close=100.,
      spread=.03):
    return QuoteCandle(time,bid_open,bid_high,bid_low,bid_close,
                       bid_open+spread,bid_high+spread,
                       bid_low+spread,bid_close+spread)


def encode(rows):
    return lzma.compress(b"".join(RECORD.pack(*r) for r in rows))


class PublicMarketTournamentTests(unittest.TestCase):
    def test_decode_public_big_endian_bars(self):
        compressed=encode([
            (0,100100,100200,100000,100300,1.),
            (60,100200,100250,100150,100300,4.)])
        x=parse_minute_file(compressed,date(2026,9,1),100000,side="BID")
        self.assertEqual(len(x),2)
        self.assertAlmostEqual(x[0][1],1.001)
        self.assertAlmostEqual(x[0][4],1.002)

    def test_reject_invalid_candles(self):
        bad=encode([(0,100000,100200,100200,100100,1.)])
        with self.assertRaisesRegex(ValueError,"invalid_public_minute_ohlc"):
            parse_minute_file(bad,date(2026,9,1),100000,side="BID")

    def test_duplicate_offsets_fail(self):
        bad=encode([(0,100000,100200,99900,100300,1.)]*2)
        with self.assertRaisesRegex(ValueError,"invalid_or_duplicate"):
            parse_minute_file(bad,date(2026,9,1),100000,side="BID")

    def test_incomplete_five_minute_candle_is_dropped(self):
        bars=[q(1_760_000_000+i*60) for i in range(5)]
        # ensure within the same natural 5-minute UTC bucket
        anchor=1_760_000_000//300*300
        bars=[q(anchor+60+i*60) for i in range(5)]
        self.assertEqual(len(aggregate(bars,5)),1)
        self.assertEqual(aggregate(bars[:4],5),[])
        self.assertEqual(aggregate(bars[1:],5),[])

    def test_no_interpolation_for_missing_bid_or_ask_day(self):
        with self.assertRaisesRegex(RuntimeError,"partial_bid_ask"):
            load_public_minutes(
                "EURUSD",date(2026,9,1),date(2026,9,2),
                fetch=lambda sym,day,side: b"data" if side=="BID" else None)

    def test_missing_both_sides_yields_no_fake_market(self):
        candles,report=load_public_minutes(
            "EURUSD",date(2026,9,1),date(2026,9,2),
            fetch=lambda *args:None)
        self.assertEqual(candles,[])
        self.assertEqual(report["empty_days"],1)

    def test_buy_stop_first_if_stop_and_target_same_bar(self):
        h=StrategyHypothesis("EURUSD","TEST","BUY","TREND_UP",
                             1_760_000_000,99.,103.,100.,.5)
        entry=q(1_760_000_300,bid_open=100.,bid_high=104,
                bid_low=98,bid_close=100.,spread=.03)
        trade=calculate_fill(h,entry,[entry])
        self.assertEqual(trade["outcome"],"SL_STOP_FIRST")
        self.assertLess(trade["R"],0)

    def test_sell_uses_ask_side_stop_and_broker_spread(self):
        h=StrategyHypothesis("EURUSD","TEST","SELL","TREND_DOWN",
                             1_760_000_000,101.,97.,100.,.5)
        entry=q(1_760_000_300,bid_open=100.,bid_high=100.5,
                bid_low=99.8,bid_close=100.,spread=.03)
        trade=calculate_fill(h,entry,[entry])
        self.assertEqual(trade["outcome"],"TIME")
        self.assertLess(trade["R"],0)

    def test_extra_cost_degrades_metrics(self):
        trades=[{"R":1.6},{"R":-1.03}]
        self.assertGreater(metrics(trades)["avg_r"],
                           metrics(trades,.2)["avg_r"])

    def test_no_performance_claim_with_no_trades(self):
        self.assertEqual(metrics([])["n"],0)
        self.assertIsNone(metrics([])["profit_factor"])

    def test_symbol_whitelist_and_bounded_scope(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                run(["XUNKNOWN"],date(2026,9,1),date(2026,9,5),
                    Path(d),fetch=lambda *args:None)
            with self.assertRaises(ValueError):
                run(["EURUSD"]*5,date(2026,9,1),date(2026,9,5),
                    Path(d),fetch=lambda *args:None)

    def test_data_source_readonly_report_with_empty_market(self):
        with tempfile.TemporaryDirectory() as d:
            report=run(["EURUSD"],date(2026,9,1),date(2026,9,3),
                       Path(d),fetch=lambda *args:None)
            self.assertEqual(report["orders_sent"],0)
            self.assertEqual(report["symbols"]["EURUSD"]["bars"]["status"],
                             "INSUFFICIENT_CLOSED_HISTORY")


if __name__=="__main__":
    unittest.main()
