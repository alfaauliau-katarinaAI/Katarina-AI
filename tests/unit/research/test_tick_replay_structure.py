"""T01/T03/T05 component tests for the tick-replay market structure (synthetic, technical only)."""
from __future__ import annotations

import math
import unittest

from katarina.research.tick_replay.bars import Bar, BarBuilder
from katarina.research.tick_replay.contract import (SIX_CANDIDATES, ReplayInputError, SessionEvidence, SymbolContract,
                                                    Tick)
from katarina.research.tick_replay.structure import Atr, MarketStructure, Zone, buffer_ticks

M15, H1 = 15 * 60_000, 60 * 60_000
SHA = "b" * 64


def bar(tf, i, o, h, l, c, length):
    return Bar(tf, i * length, (i + 1) * length, o, h, l, c, 4, 20)


class Recorder:
    def __init__(self):
        self.events = []

    def __call__(self, event_type, **fields):
        self.events.append((event_type, fields))


def structure():
    rec = Recorder()
    return MarketStructure(SIX_CANDIDATES["B1"], emit=rec, sessions=None), rec


class PivotTests(unittest.TestCase):
    def feed(self, ms, rows, tf="M15", length=M15):
        for i, row in enumerate(rows):
            ms.on_bar(bar(tf, i, *row, length))

    def test_pivot_needs_two_closed_right_bars(self):
        ms, _ = structure()
        rows = [(10, 12, 9, 11), (11, 13, 10, 12), (12, 20, 11, 15), (15, 16, 12, 13)]
        self.feed(ms, rows)
        self.assertEqual([], [s for s in ms.tf["M15"].swings if s.kind == "HIGH"])
        ms.on_bar(bar("M15", 4, 13, 14, 11, 12, M15))
        highs = [s for s in ms.tf["M15"].swings if s.kind == "HIGH"]
        self.assertEqual(1, len(highs))
        self.assertEqual(20, highs[0].level)
        self.assertEqual(5 * M15, highs[0].confirmed_at_ms)       # known at the close of the 2nd right bar
        self.assertIsNone(ms.latest_swing("M15", "HIGH", known_before_ms=5 * M15 - 1, at_ms=5 * M15 - 1))

    def test_equal_highs_left_strict_right_nonstrict(self):
        ms, _ = structure()
        rows = [(10, 12, 9, 11), (11, 13, 10, 12), (12, 20, 11, 15), (15, 20, 12, 13), (13, 14, 11, 12),
                (12, 13, 10, 11)]
        self.feed(ms, rows)
        highs = [s for s in ms.tf["M15"].swings if s.kind == "HIGH"]
        self.assertEqual([2 * M15], [s.bar_start_ms for s in highs])   # earliest of the equal highs only

    def test_m15_ttl_96_boundary(self):
        ms, _ = structure()
        rows = [(10, 12, 9, 11), (11, 13, 10, 12), (12, 20, 11, 15), (15, 16, 12, 13), (13, 14, 11, 12)]
        self.feed(ms, rows)
        swing = next(s for s in ms.tf["M15"].swings if s.kind == "HIGH")
        for i in range(5, 5 + 96):
            ms.on_bar(bar("M15", i, 12, 13, 11, 12, M15))
        self.assertEqual("VALID", swing.status)
        ms.on_bar(bar("M15", 101, 12, 13, 11, 12, M15))
        self.assertEqual("EXPIRED_TTL", swing.status)

    def test_close_beyond_by_one_tick_invalidates(self):
        ms, _ = structure()
        rows = [(10, 12, 9, 11), (11, 13, 10, 12), (12, 20, 11, 15), (15, 16, 12, 13), (13, 14, 11, 12)]
        self.feed(ms, rows)
        swing = next(s for s in ms.tf["M15"].swings if s.kind == "HIGH")
        ms.on_bar(bar("M15", 5, 12, 20, 11, 20, M15))     # close equal to level: still valid
        self.assertEqual("VALID", swing.status)
        ms.on_bar(bar("M15", 6, 20, 22, 19, 21, M15))
        self.assertEqual("INVALIDATED", swing.status)

    def test_invalid_bar_expires_swings_and_resets_atr(self):
        ms, _ = structure()
        rows = [(10, 12, 9, 11), (11, 13, 10, 12), (12, 20, 11, 15), (15, 16, 12, 13), (13, 14, 11, 12)]
        self.feed(ms, rows)
        gap = bar("M15", 5, 12, 13, 11, 12, M15)
        gap.valid, gap.invalid_reason = False, "QUOTE_GAP_INSIDE_SESSION"
        ms.on_bar(gap)
        self.assertTrue(all(s.status == "EXPIRED_GAP" for s in ms.tf["M15"].swings))
        self.assertIsNone(ms.tf["M15"].atr.value)


class AtrBufferTests(unittest.TestCase):
    def test_wilder_seed_and_smoothing(self):
        atr = Atr(14)
        bars = [bar("M5", 0, 100, 100, 100, 100, 1)] + [bar("M5", i, 100, 110, 100, 100, 1) for i in range(1, 15)]
        for b in bars:
            atr.update(b)
        self.assertEqual(10.0, atr.value)
        atr.update(bar("M5", 15, 100, 124, 100, 100, 1))
        self.assertAlmostEqual((10.0 * 13 + 24) / 14, atr.value)

    def test_warmup_returns_none(self):
        self.assertIsNone(buffer_ticks(20, None, 0.10))

    def test_buffer_is_max_of_tick_spread_and_ceiled_atr(self):
        self.assertEqual(20, buffer_ticks(20, 150.0, 0.10))
        self.assertEqual(31, buffer_ticks(20, 301.0, 0.10))      # ceil(30.1) -> 31 ticks
        self.assertEqual(30, buffer_ticks(20, 300.0, 0.10))      # exact value is not pushed up by float noise
        self.assertEqual(1, buffer_ticks(0, 0.0, 0.10))


class ZoneTests(unittest.TestCase):
    def zone(self, ms, zone_id, low, high, confirmed):
        z = Zone(zone_id, "DEMAND", low, high, confirmed, 0, "H1:HIGH:0")
        ms.zones.append(z)
        return z

    def test_overlap_selects_nearest_proximal_then_newest(self):
        ms, rec = structure()
        far = self.zone(ms, "DEMAND:1", 900, 1050, 300)      # newest, but its proximal is further from BID
        near_old = self.zone(ms, "DEMAND:2", 920, 1000, 100)
        near_new = self.zone(ms, "DEMAND:3", 930, 1000, 200)
        ms.apply_zone_tick(Tick(1, 1000, 990, 1010), 0, 5, event_id="T1")
        self.assertEqual("FIRST_VISIT_PENDING_M15", near_new.status)
        self.assertEqual(("CONSUMED", "CONSUMED_OVERLAP_NOT_SELECTED"), (near_old.status, near_old.reason))
        self.assertEqual("CONSUMED", far.status)
        touch = [f for e, f in rec.events if e == "ZONE_FIRST_TOUCH"][0]
        self.assertEqual("DEMAND:3", touch["selected_zone_id"])
        self.assertEqual(["DEMAND:1", "DEMAND:2"], sorted(touch["consumed_zone_ids"]))

    def test_hybrid_breach_then_h1_close(self):
        for close, expected in ((950, "CONSUMED"), (850, "INVALID")):
            ms, _ = structure()
            z = self.zone(ms, "DEMAND:1", 900, 1000, 0)
            ms.apply_zone_tick(Tick(1, 10, 880, 900), 0, 5, event_id="T1")    # below 900 - 5: touch then breach
            self.assertEqual("BREACH_LOCKED", z.status)
            ms._zones_on_h1(bar("H1", 0, 1000, 1000, 880, close, H1))
            self.assertEqual(expected, z.status)

    def test_zone_ttl_48_h1(self):
        ms, _ = structure()
        z = self.zone(ms, "DEMAND:1", 900, 1000, 0)
        for i in range(48):
            ms._zones_on_h1(bar("H1", i, 1100, 1200, 1050, 1100, H1))
        self.assertEqual("FRESH", z.status)
        ms._zones_on_h1(bar("H1", 48, 1100, 1200, 1050, 1100, H1))
        self.assertEqual(("EXPIRED", "ZONE_TTL_48_H1"), (z.status, z.reason))


class BarAndContractTests(unittest.TestCase):
    def test_half_open_interval_and_close_due(self):
        b = BarBuilder("M5", sequence_verified=False)
        b.add(Tick(0, 1_000, 100, 110))
        self.assertIsNone(b.close_due(299_999))
        closed = b.close_due(300_000)                 # a tick exactly at end belongs to the next candle
        self.assertEqual((0, 300_000), (closed.start_ms, closed.end_ms))

    def test_unverified_same_ms_close_is_ambiguous(self):
        b = BarBuilder("M5", sequence_verified=False)
        for seq, bid in enumerate((100, 105, 101)):
            b.add(Tick(seq, 1_000 + (seq // 2) * 1000, bid, bid + 10))
        b.add(Tick(3, 2_000, 99, 109))
        closed = b.close_due(300_000)
        self.assertTrue(closed.close_ambiguous)
        verified = BarBuilder("M5", sequence_verified=True)
        for seq, bid in enumerate((100, 105)):
            verified.add(Tick(seq, 1_000, bid, bid + 10))
        self.assertFalse(verified.close_due(300_000).close_ambiguous)

    def test_price_grid_is_enforced(self):
        contract = SymbolContract("XAUUSD.vx", 2, 0.01, 0.01, 31, 0, 100.0, SHA)
        self.assertEqual(400_012, contract.to_ticks(4000.12))
        with self.assertRaises(ReplayInputError) as ctx:
            contract.to_ticks(4000.125)
        self.assertEqual("PRICE_OFF_TICK_GRID", ctx.exception.reason)
        self.assertEqual(31, contract.stops_level_ticks)

    def test_session_evidence_must_be_sorted_and_disjoint(self):
        with self.assertRaises(ReplayInputError) as ctx:
            SessionEvidence(((0, 10), (5, 20)), ((0, 10),), "x", SHA)
        self.assertEqual("SESSION_EVIDENCE_INVALID", ctx.exception.reason)
        s = SessionEvidence(((0, 10), (20, 30)), ((0, 10),), "x", SHA)
        self.assertEqual(10, s.quote_overlap_ms(5, 25))

    def test_candidate_table_is_the_owner_registered_one(self):
        expected = {"B1": ("BUY", "SWEEP_RECLAIM", "M5", 12, 90, 15), "S1": ("SELL", "SWEEP_RECLAIM", "M5", 12, 90, 15),
                    "B2": ("BUY", "ZONE_PULLBACK", "M15", 12, 240, 30), "S2": ("SELL", "ZONE_PULLBACK", "M15", 12, 240, 30),
                    "B3": ("BUY", "BREAKOUT_RETEST", "M5", 24, 180, 20),
                    "S3": ("SELL", "BREAKOUT_RETEST", "M5", 24, 180, 20)}
        got = {k: (c.side, c.setup, c.entry_tf, c.time_exit_bars, c.time_exit_minutes, c.preclose_minutes)
               for k, c in SIX_CANDIDATES.items()}
        self.assertEqual(expected, got)
        for c in SIX_CANDIDATES.values():
            self.assertEqual((2, 2, 0.10, 14, 48, 12, 6), (c.pivot_left, c.pivot_right, c.atr_buffer_fraction,
                                                           c.atr_period, c.zone_ttl_h1, c.zone_origin_lookback_h1,
                                                           c.retest_max_m5))
        self.assertEqual(6, len({c.spec_sha256 for c in SIX_CANDIDATES.values()}))
        self.assertTrue(math.isfinite(SIX_CANDIDATES["B1"].atr_buffer_fraction))


if __name__ == "__main__":
    unittest.main()
