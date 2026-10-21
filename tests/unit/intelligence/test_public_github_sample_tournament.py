"""Tests for public M5 source model; all network access mocked."""
import unittest
from unittest.mock import patch
from datetime import date
from io import BytesIO
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"scripts"/"research"))
import public_github_sample_tournament as tournament_module
from public_github_sample_tournament import (
    load_public_sample,h1_from_m5,tournament,PUBLIC_SAMPLES)
from public_market_tournament import QuoteCandle
from katarina.intelligence.lab.adaptive_strategy_library import StrategyHypothesis


class Response:
    def __init__(self,s):self.stream=BytesIO(s.encode())
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n):return self.stream.read(n)


class PublicSampleTournamentTests(unittest.TestCase):
    def fixture(self):
        return ("datetime,open,high,low,close,volume\n"
                "2026-08-17T10:00:00+00:00,1.1000,1.1003,1.0998,1.1002,100\n"
                "2026-08-17T10:05:00+00:00,1.1002,1.1005,1.1001,1.1003,150\n")

    def test_csv_reference_not_marked_bid_ask_verified(self):
        rows,report=load_public_sample(
            "EURUSD",date(2026,8,17),date(2026,8,18),
            opener=lambda *args,**kw:Response(self.fixture()))
        self.assertEqual(len(rows),2)
        self.assertFalse(report["actual_historical_bid_ask_available"])
        self.assertGreater(rows[0].ask_open,rows[0].bid_open)

    def test_future_rows_not_in_replay_range(self):
        data=self.fixture()+("2026-08-19T10:00:00+00:00,"
                             "1.1,1.101,1.099,1.1,100\n")
        rows,_=load_public_sample(
            "EURUSD",date(2026,8,17),date(2026,8,18),
            opener=lambda *args,**kw:Response(data))
        self.assertEqual(len(rows),2)

    def test_duplicate_timestamp_rejected(self):
        data=self.fixture()+self.fixture().splitlines()[-1]+"\n"
        with self.assertRaisesRegex(ValueError,"duplicate"):
            load_public_sample(
                "EURUSD",date(2026,8,17),date(2026,8,18),
                opener=lambda *args,**kw:Response(data))

    def test_timezone_aware_source_required(self):
        data=self.fixture().replace("+00:00","")
        with self.assertRaisesRegex(ValueError,"unknown_market_timezone"):
            load_public_sample(
                "EURUSD",date(2026,8,17),date(2026,8,18),
                opener=lambda *args,**kw:Response(data))

    def test_h1_must_be_complete_twelve_m5(self):
        a=1_760_000_000//3600*3600
        bars=[QuoteCandle(a+300*(i+1),1,1.1,.9,1,
                          1.02,1.12,.92,1.02) for i in range(12)]
        self.assertEqual(len(h1_from_m5(bars)),1)
        self.assertEqual(h1_from_m5(bars[:-1]),[])

    def test_m5_symbol_without_enough_H1_has_no_trades(self):
        trades,report=tournament("EURUSD",[])
        self.assertEqual(trades,[])
        self.assertEqual(report["status"],"INSUFFICIENT_HISTORY")

    def test_oil_and_indices_price_scale_in_fill_model(self):
        base=(1_760_000_000//3600)*3600
        bars=[QuoteCandle(base+(i+1)*300,100.,100.4,99.6,100.,
                          100.05,100.45,99.65,100.05) for i in range(260)]
        hypothesis=StrategyHypothesis(
            "USOIL","TREND_PULLBACK","BUY","TREND_UP",
            base+240*300,90.,120.,100.,.8)
        with patch.object(tournament_module,"propose_closed_candle_strategies",
                          return_value=(hypothesis,)):
            for symbol in ("USOIL","US30","NAS100"):
                trades,detail=tournament_module.tournament(symbol,bars)
                self.assertEqual(detail["status"],"OK")
                self.assertGreater(len(trades),0)

    def test_only_verified_samples_accepted(self):
        self.assertEqual(set(PUBLIC_SAMPLES),{
            "EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURGBP",
            "EURJPY","XAUUSD","USOIL","US30","NAS100"})
        from public_github_sample_tournament import POINT_SCALE,UNVERIFIED_SCOPE
        self.assertEqual(POINT_SCALE["NAS100"],1)
        self.assertEqual(POINT_SCALE["USOIL"],100)
        self.assertIn("BTCUSD",UNVERIFIED_SCOPE)
        with self.assertRaisesRegex(ValueError,"unverified_public_github_sample"):
            load_public_sample("BTCUSD",date(2026,8,17),date(2026,8,18))


if __name__=="__main__":
    unittest.main()
