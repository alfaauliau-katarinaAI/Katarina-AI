"""WP1: explicit broker core symbols must never be silently truncated."""
from pathlib import Path
import json
from types import SimpleNamespace
import tempfile
import unittest

from katarina.intelligence.broker.observer_universe import (
    ObserverUniverse, load_universe, select_symbols,
)


def sym(name, mode=4):
    return SimpleNamespace(name=name, trade_mode=mode)


class ObserverUniverseTests(unittest.TestCase):
    def test_matches_frozen_alpha_program_and_gold_first(self):
        universe = load_universe("config/observer_universe.json")
        alpha = json.loads(Path(
            "config/research/alpha_regime_program_v1.json").read_text())
        self.assertEqual(set(universe.core), set(alpha["symbols"]))
        self.assertEqual(universe.core[0], "XAUUSD.vx")
        self.assertEqual(universe.rotating_slots, 0)

    def test_explicit_core_order_and_missing_disabled_accounted(self):
        universe = ObserverUniverse(("XAUUSD.vx", "NAS100.vx", "EURUSD.vx"))
        selected, missing = select_symbols(
            universe, [sym("EURUSD.vx"), sym("NAS100.vx", 0),
                       sym("XAUUSD.vx"), sym("US30.vx")])
        self.assertEqual(selected, ("XAUUSD.vx", "EURUSD.vx"))
        self.assertEqual(missing, ("NAS100.vx",))

    def test_rotation_excludes_core_deduplicates_and_limits_to_17(self):
        universe = ObserverUniverse(("XAUUSD.vx", "EURUSD.vx"), 3)
        catalog = [sym(s) for s in
                   ("XAUUSD.vx", "EURUSD.vx", "GBPUSD.vx", "USDJPY.vx", "AUDUSD.vx")]
        seen = []
        def rotation(budget, exclude):
            seen.append((budget, exclude))
            return ["XAUUSD.vx", "GBPUSD.vx", "GBPUSD.vx",
                    "USDJPY.vx", "AUDUSD.vx"]
        chosen, missing = select_symbols(universe, catalog, rotation=rotation)
        self.assertEqual(missing, ())
        self.assertEqual(chosen, ("XAUUSD.vx", "EURUSD.vx",
                                  "GBPUSD.vx", "USDJPY.vx", "AUDUSD.vx"))
        self.assertEqual(seen, [(3, ("XAUUSD.vx", "EURUSD.vx"))])

    def test_rotation_never_fills_missing_core_with_extra_slots(self):
        universe = ObserverUniverse(
            ("XAUUSD.vx", "NAS100.vx", "US30.vx", "JPN225.vx"), 2)
        catalog = [sym(x) for x in
                   ("XAUUSD.vx", "A.vx", "B.vx", "C.vx", "D.vx")]
        chosen, missing = select_symbols(
            universe, catalog,
            rotation=lambda budget, exclude: ["A.vx", "B.vx", "C.vx", "D.vx"])
        self.assertEqual(chosen, ("XAUUSD.vx", "A.vx", "B.vx"))
        self.assertEqual(missing, ("NAS100.vx", "US30.vx", "JPN225.vx"))

    def test_bad_config_is_rejected_before_mt5(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "u.json"
            for body in (
                {"schema_version": 1, "core": [], "rotating_slots": 0},
                {"schema_version": 1, "core": ["A", "A"], "rotating_slots": 0},
                {"schema_version": 1, "core": ["A", 1], "rotating_slots": 0},
                {"schema_version": 1, "core": ["A"], "rotating_slots": True},
                {"schema_version": 1, "core": ["A"], "rotating_slots": 11},
                {"schema_version": 1, "core": ["A"] * 8,
                 "rotating_slots": 10},
            ):
                p.write_text(json.dumps(body), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_universe(p)

    def test_disabled_and_missing_symbols_do_not_use_aliases(self):
        core = ObserverUniverse(("XAUUSD.vx", "NAS100.vx"))
        chosen, missing = select_symbols(
            core, [sym("XAUUSD"), sym("NAS100.vx", 3)])
        self.assertEqual(chosen, ())
        self.assertEqual(missing, ("XAUUSD.vx", "NAS100.vx"))

    def test_existing_lab_rotation_can_exclude_core(self):
        import sqlite3
        from contextlib import closing
        from datetime import datetime, timezone
        from katarina.intelligence.lab.continuous_research_lab import select_batch
        now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
        catalog = [sym(x) for x in
                   ("XAUUSD.vx", "EURUSD.vx", "USDJPY.vx", "GBPUSD.vx")]
        with closing(sqlite3.connect(":memory:")) as db:
            chosen = select_batch(db, catalog, 2, now,
                                  exclude=("XAUUSD.vx", "EURUSD.vx"))
        self.assertEqual(chosen, ["GBPUSD.vx", "USDJPY.vx"])

    def test_invalid_universe_instance_is_rejected(self):
        with self.assertRaises(ValueError):
            ObserverUniverse(("A", "A"))
        with self.assertRaises(ValueError):
            ObserverUniverse(("A",), 17)


if __name__ == "__main__":
    unittest.main()
