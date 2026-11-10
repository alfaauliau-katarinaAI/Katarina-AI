"""T02-T12 scenario tests for the six-candidate tick-replay engine.

Synthetic fixtures check rules only; no test measures or reports trading performance (Owner order K1).
"""
from __future__ import annotations

import unittest
from dataclasses import replace

from katarina.research.tick_replay import SIX_CANDIDATES, ReplayInputError, SymbolContract, Tick
from katarina.research.tick_replay.contract import DEV_CUTOFF_MS

from tests.unit.research._tick_replay_fixtures import (B1_M15, B1_SWEEP_START, BASE, CONTRACT, DAY0, H1, MIN, SHA, SPREAD,
                                                       H1_TREND_UP, Path, b1_path, b2_path, b3_path, events, run,
                                                       sessions)

TP_TICK = {"B1": (B1_SWEEP_START + 6 * MIN, 1550), "B2": (DAY0 + 15 * H1 + 40 * MIN, 1750),
           "B3": (DAY0 + 13 * H1 + 10 * MIN, 2050)}
PATHS = {"B1": b1_path, "B2": b2_path, "B3": b3_path}


def strip(evts):
    return [{k: v for k, v in e.items() if k != "n"} for e in evts]


class SixCandidateEntryExitTests(unittest.TestCase):
    """T02/T03/T04/T06: each candidate fires on its own rule, enters at ASK (BUY) / BID (SELL)."""

    def test_each_candidate_enters_and_exits_on_the_right_side_of_the_quote(self):
        for buy in ("B1", "B2", "B3"):
            for mirror in (False, True):
                cid = buy if not mirror else "S" + buy[1]
                with self.subTest(candidate=cid):
                    path = PATHS[buy]().at(*TP_TICK[buy])
                    ticks = path.ticks(mirror=mirror)
                    replay, result = run(ticks)
                    fills = [c for c, v in result["candidates"].items() if v["trades"]]
                    self.assertEqual([cid], fills, "only the candidate under test may trade")
                    entry = events(replay, cid, "ENTRY_FILLED")[0]
                    exit_ = events(replay, cid, "EXIT_FILLED")[0]
                    tick_in = ticks[entry["source_tick_seq"]]
                    tick_out = ticks[exit_["source_tick_seq"]]
                    if mirror:
                        self.assertEqual(CONTRACT.price(tick_in.bid), entry["fill_price"])
                        self.assertEqual(CONTRACT.price(tick_out.ask), exit_["fill_price"])
                    else:
                        self.assertEqual(CONTRACT.price(tick_in.ask), entry["fill_price"])
                        self.assertEqual(CONTRACT.price(tick_out.bid), exit_["fill_price"])
                    self.assertEqual("TAKE_PROFIT", exit_["intended_exit_reason"])
                    intent = events(replay, cid, "ENTRY_INTENT")[0]
                    boundary = [t for t in ticks if t.time_ms >= intent["bar_closed_at_ms"]][0]
                    self.assertGreater(entry["source_tick_seq"], boundary.seq, "no fill on the revealing tick")
                    self.assertEqual(SIX_CANDIDATES[cid].spec_sha256, entry["hypothesis_spec_sha256"])

    def test_b1_stop_is_structure_minus_buffer_and_tp_is_structural(self):
        replay, _ = run(b1_path().ticks())
        intent = events(replay, "B1", "ENTRY_INTENT")[0]
        self.assertGreaterEqual(intent["buffer_ticks"], SPREAD)
        self.assertEqual(CONTRACT.price(BASE + 490 - intent["buffer_ticks"]), intent["stop"])
        entry = events(replay, "B1", "ENTRY_FILLED")[0]
        self.assertEqual(CONTRACT.price(BASE + 1500), entry["target"])
        self.assertTrue(entry["target_id"].startswith("M15:HIGH:"))

    def test_b1_stop_loss_fills_at_bid_and_marks_gap_through_stop(self):
        path = b1_path().at(B1_SWEEP_START + 6 * MIN, 300)       # gaps below the stop
        replay, result = run(path.ticks())
        trade = result["candidates"]["B1"]["trades"][0]
        self.assertEqual("STOP_LOSS", trade["exit_reason"])
        self.assertEqual(CONTRACT.price(BASE + 300), trade["exit_price"])
        self.assertTrue(trade["fill_beyond_stop"])

    def test_b2_unconfirmed_first_visit_consumes_zone(self):
        p = Path().bars(H1, H1_TREND_UP)
        t = DAY0 + 15 * H1
        p.at(t + 15 * MIN + 1_000, 1250).at(t + 20 * MIN, 1190).at(t + 29 * MIN, 1240)   # bearish touch candle
        p.at(t + 31 * MIN, 1300).at(t + 46 * MIN, 1190).at(t + 59 * MIN, 1260)           # later touch: no 2nd visit
        replay, _ = run(p.ticks())
        self.assertEqual([], events(replay, "B2", "ENTRY_INTENT"))
        states = [e for e in replay.events if e["event_type"] == "ZONE_STATE" and e.get("candidate_scope") == "B2"]
        self.assertEqual(["FIRST_VISIT_NOT_CONFIRMED"], [e["reason"] for e in states])

    def test_b3_without_valid_target_is_blocked(self):
        p = Path().bars(H1, H1_TREND_UP[:13])
        t = DAY0 + 13 * H1
        p.at(t + 1_000, 1520).at(t + 2 * MIN, 1495).at(t + 4 * MIN, 1560).at(t + 5 * MIN + 1_000, 1560)
        p.at(t + 5 * MIN + 2_000, 1560)
        replay, _ = run(p.ticks())
        blocked = events(replay, "B3", "ENTRY_BLOCKED")
        self.assertEqual(["WAIT:NO_VALID_STRUCTURAL_TARGET"], [e["reason_code"] for e in blocked])

    def test_b3_retest_times_out_after_six_m5(self):
        replay, _ = run(b2_path().ticks())
        reasons = [e.get("reason") for e in replay.events if e["event_type"] == "BREAKOUT_SETUP_CLOSED"]
        self.assertIn("WAIT:RETEST_TIMEOUT", reasons)
        self.assertEqual([], events(replay, "B3", "ENTRY_INTENT"))

    def test_broker_stops_level_blocks_too_close_geometry(self):
        wide = replace(CONTRACT, stops_level_points=5_000)
        replay, _ = run(b1_path().ticks(), contract=wide)
        self.assertEqual(["WAIT:INVALID_BROKER_STOP_GEOMETRY"],
                         [e["reason_code"] for e in events(replay, "B1", "ENTRY_BLOCKED")])


class SessionAndTimeExitTests(unittest.TestCase):
    """T06/T08/T09: session evidence, pre-close, bar/UTC time exits, no quote at expiry."""

    def test_missing_session_evidence_blocks_entry(self):
        replay, _ = run(b1_path().ticks(), sess=None)
        self.assertEqual(["BLOCKED_SESSION_EVIDENCE"],
                         [e["reason_code"] for e in events(replay, "B1", "ENTRY_BLOCKED")])

    def test_quote_open_but_trade_closed_blocks_entry(self):
        fill_time = B1_SWEEP_START + 5 * MIN
        s = sessions(trade=((DAY0, fill_time),))
        replay, _ = run(b1_path().ticks(), sess=s)
        self.assertEqual(["WAIT:TRADE_SESSION_CLOSED"],
                         [e["reason_code"] for e in events(replay, "B1", "ENTRY_BLOCKED")])

    def test_preclose_window_blocks_entry(self):
        s = sessions(B1_SWEEP_START + 5 * MIN + 10 * MIN)          # trade ends 10 min after fill; B1 pre-close 15
        replay, _ = run(b1_path().ticks(), sess=s)
        self.assertEqual(["WAIT:PRECLOSE_ENTRY_BLOCK"],
                         [e["reason_code"] for e in events(replay, "B1", "ENTRY_BLOCKED")])

    def test_preclose_time_exit(self):
        fill = B1_SWEEP_START + 5 * MIN + 2_000
        s = sessions(fill + 40 * MIN)
        path = b1_path()
        for minute in range(1, 30):
            path.at(fill + minute * MIN, 700)
        replay, result = run(path.ticks(), sess=s)
        trade = result["candidates"]["B1"]["trades"][0]
        self.assertEqual("TIME_EXIT_PRECLOSE", trade["exit_reason"])
        self.assertGreaterEqual(trade["exit_ms"], fill + 25 * MIN)

    def test_bar_count_time_exit_fills_after_the_twelfth_closed_m5(self):
        fill = B1_SWEEP_START + 5 * MIN + 2_000
        path = b1_path()
        for minute in range(1, 75):
            path.at(fill + minute * MIN, 700)
        replay, result = run(path.ticks())
        trade = result["candidates"]["B1"]["trades"][0]
        self.assertEqual("TIME_EXIT_BARS", trade["exit_reason"])
        intent = [e for e in events(replay, "B1", "EXIT_INTENT")][0]
        self.assertEqual(12, intent["bars"])
        self.assertGreater(trade["exit_ms"], intent["at_ms"])        # filled after the boundary, not on it

    def test_utc_time_exit_when_bars_are_sparse(self):
        fill = B1_SWEEP_START + 5 * MIN + 2_000
        path = b1_path()
        for minute in range(20, 121, 20):
            path.at(fill + minute * MIN, 700)
        replay, result = run(path.ticks(), max_gap_ms=60 * MIN)
        trade = result["candidates"]["B1"]["trades"][0]
        self.assertEqual("TIME_EXIT_UTC", trade["exit_reason"])
        self.assertEqual(fill + 100 * MIN, trade["exit_ms"])

    def test_no_trade_quote_at_expiry_waits_for_next_trade_quote(self):
        fill = B1_SWEEP_START + 5 * MIN + 2_000
        closed_from = fill + 85 * MIN
        s = sessions(trade=((DAY0, closed_from), (closed_from + 60 * MIN, DAY0 + 7 * 86_400_000)))
        path = b1_path()
        for minute in list(range(20, 61, 20)) + list(range(100, 181, 20)):   # no tick in the pre-close window
            path.at(fill + minute * MIN, 700)
        replay, result = run(path.ticks(), sess=s, max_gap_ms=60 * MIN)
        self.assertEqual(1, len(events(replay, "B1", "EXIT_PENDING_NO_QUOTE")))
        trade = result["candidates"]["B1"]["trades"][0]
        self.assertIn(trade["exit_reason"], ("TIME_EXIT_UTC", "TIME_EXIT_PRECLOSE"))
        self.assertGreaterEqual(trade["exit_ms"], closed_from + 60 * MIN)

    def test_quote_gap_between_signal_and_fill_blocks_entry_and_invalidates_candles(self):
        path = Path().bars(15 * MIN, B1_M15)
        t = B1_SWEEP_START
        path.at(t + 1_000, 560).at(t + 2 * MIN, 490).at(t + 5 * MIN - 1_000, 600)
        path.at(t + 5 * MIN + 1_000, 610).at(t + 50 * MIN, 600)
        replay, _ = run(path.ticks(), max_gap_ms=30 * MIN)
        self.assertEqual(["BLOCKED_DATA_GAP"], [e["reason_code"] for e in events(replay, "B1", "ENTRY_BLOCKED")])
        gaps = [e for e in replay.events if e["event_type"] == "DATA_GAP"]
        self.assertEqual(1, len(gaps))

    def test_open_position_at_data_end_is_reported_not_closed(self):
        replay, result = run(b1_path().ticks())
        self.assertEqual(1, len(events(replay, "B1", "OPEN_AT_DATA_END")))
        self.assertEqual([], result["candidates"]["B1"]["trades"])
        self.assertTrue(result["candidates"]["B1"]["open_at_data_end"])


class OrderingTests(unittest.TestCase):
    """T07: an unprovable same-millisecond order blocks; it is never resolved by an OHLC/SL-first fallback."""

    def same_ms_fill_path(self):
        p = b1_path()
        p.points.pop()                                            # replace the single fill tick by a group
        t = B1_SWEEP_START + 5 * MIN + 2_000
        return p.at(t, 600).at(t, 640)

    def test_unverified_group_blocks(self):
        replay, result = run(self.same_ms_fill_path().ticks(), seq="UNVERIFIED")
        self.assertEqual(["BLOCKED_INTRABAR_ORDER"], [e["reason_code"] for e in events(replay, "B1", "ENTRY_BLOCKED")])
        self.assertEqual([], events(replay, "B1", "ENTRY_FILLED"))

    def test_verified_source_order_fills_on_first_tick(self):
        ticks = self.same_ms_fill_path().ticks()
        replay, _ = run(ticks, seq="VERIFIED_SOURCE_ORDER")
        entry = events(replay, "B1", "ENTRY_FILLED")[0]
        self.assertEqual(ticks[-2].seq, entry["source_tick_seq"])

    def test_same_ms_group_hitting_stop_and_target_blocks_position(self):
        p = b1_path()
        t = B1_SWEEP_START + 6 * MIN
        p.at(t, 1550).at(t, 300)
        replay, result = run(p.ticks())
        self.assertEqual(["BLOCKED_INTRABAR_ORDER"],
                         [e["reason_code"] for e in events(replay, "B1", "POSITION_BLOCKED")])
        self.assertEqual([], result["candidates"]["B1"]["trades"])


class IndependenceDeterminismTests(unittest.TestCase):
    """T10/T11: six isolated experiments, one position each, deterministic ledger, no lookahead, no holdout."""

    def test_candidate_events_do_not_depend_on_other_candidates(self):
        ticks = b1_path().at(*TP_TICK["B1"]).ticks()
        full, _ = run(ticks)
        alone, _ = run(ticks, candidates=[SIX_CANDIDATES["B1"]])
        self.assertEqual(strip(events(full, "B1")), strip(events(alone, "B1")))

    def test_second_signal_while_position_open_is_skipped(self):
        p = b1_path()
        t = B1_SWEEP_START + 10 * MIN
        p.at(t + 1_000, 560).at(t + 2 * MIN, 480).at(t + 5 * MIN - 1_000, 600).at(t + 5 * MIN + 1_000, 600)
        replay, _ = run(p.ticks())
        skipped = events(replay, "B1", "SIGNAL_SKIPPED")
        self.assertEqual(["WAIT:POSITION_ACTIVE"], [e["reason_code"] for e in skipped])
        self.assertEqual(1, len(events(replay, "B1", "ENTRY_FILLED")))

    def test_same_inputs_same_ledger_hash(self):
        ticks = b2_path().at(*TP_TICK["B2"]).ticks()
        _, a = run(ticks)
        _, b = run(list(ticks))
        self.assertEqual(a["ledger_sha256"], b["ledger_sha256"])
        self.assertEqual(0, a["orders_sent"])
        self.assertFalse(a["live_execution_authorized"])

    def test_future_ticks_do_not_change_past_events(self):
        base = b3_path().ticks()
        cut = base[-1].time_ms
        poisoned = base + [Tick(len(base) + i, cut + (i + 1) * MIN, BASE + 5000 - i, BASE + 5020 - i)
                           for i in range(50)]
        a, _ = run(base)
        b, _ = run(poisoned)
        past = [e for e in strip(b.events) if e.get("at_ms", 0) <= cut and e["event_type"] not in
                ("OPEN_AT_DATA_END", "ENTRY_BLOCKED")]
        before = [e for e in strip(a.events) if e["event_type"] not in ("OPEN_AT_DATA_END", "ENTRY_BLOCKED")]
        self.assertEqual(before, past[:len(before)])

    def test_holdout_and_invalid_quotes_are_refused(self):
        with self.assertRaises(ReplayInputError) as ctx:
            run([Tick(0, DEV_CUTOFF_MS, BASE, BASE + 20)])
        self.assertEqual("HOLDOUT_DATA_FORBIDDEN", ctx.exception.reason)
        for bad, reason in (([Tick(0, DAY0, BASE, BASE)], "QUOTE_INVALID"),
                            ([Tick(0, DAY0 + 5, BASE, BASE + 1), Tick(1, DAY0, BASE, BASE + 1)], "TICK_OUT_OF_ORDER"),
                            ([], "TICK_DATA_EMPTY")):
            with self.assertRaises(ReplayInputError) as ctx:
                run(bad)
            self.assertEqual(reason, ctx.exception.reason)

    def test_symbol_mismatch_is_refused(self):
        other = SymbolContract("EURUSD", 5, 0.00001, 0.00001, 0, 0, 100000.0, SHA)
        with self.assertRaises(ReplayInputError) as ctx:
            run(b1_path().ticks(), contract=other)
        self.assertEqual("SYMBOL_MISMATCH", ctx.exception.reason)


class CostRecordTests(unittest.TestCase):
    """T12: costs come from the registered snapshot and are recorded per trade, never aggregated here."""

    def test_trade_records_spreads_commission_and_swap_nights(self):
        fill = B1_SWEEP_START + 5 * MIN + 2_000
        path = b1_path()
        rollover = DAY0 + 21 * 60 * MIN
        path.at(rollover - MIN, 700).at(rollover + MIN, 700).at(rollover + 2 * MIN, 1550)
        long_hold = replace(SIX_CANDIDATES["B1"], time_exit_bars=10_000, time_exit_minutes=10_000)
        replay, result = run(path.ticks(), candidates=[long_hold], max_gap_ms=24 * 60 * MIN)
        trade = result["candidates"]["B1"]["trades"][0]
        self.assertGreater(rollover, fill)
        self.assertEqual(1, trade["swap_nights"])
        self.assertEqual(-30.0, trade["swap_per_lot"])
        self.assertEqual(7.0, trade["commission_per_lot"])
        self.assertEqual(SPREAD, trade["entry_spread_ticks"])
        self.assertEqual(result["input_hashes"]["costs"], trade["cost_snapshot_sha256"])
        for key in ("net", "profit", "pnl", "win_rate", "expectancy"):
            self.assertNotIn(key, result)


if __name__ == "__main__":
    unittest.main()
