"""Official assessment must not expose a historical rollover override."""
import contextlib
import io
import sqlite3
import unittest
from datetime import datetime, timezone

from katarina.intelligence.operations import data_health, observation_ledger
from scripts.ai.check_stage0_health import main


class NonretroactiveRolloverTest(unittest.TestCase):
    def test_assessor_rejects_retroactive_override(self):
        with sqlite3.connect(":memory:") as db:
            with self.assertRaises(TypeError):
                data_health.assess(db, datetime(2026, 11, 2, tzinfo=timezone.utc),
                                   effective_utc="2026-01-01T00:00:00Z")

    def test_cli_rejects_retroactive_override(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["--state-dir", "unused", "--effective-utc", "2026-01-01T00:00:00Z"])
        self.assertEqual(error.exception.code, 2)

    def test_activation_stays_disabled(self):
        self.assertIsNone(observation_ledger.ROLLOVER_RULE_EFFECTIVE_UTC)
