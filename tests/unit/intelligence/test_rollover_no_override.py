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

    def test_activation_is_the_owner_decision_and_prospective(self):
        effective = datetime.fromisoformat(observation_ledger.ROLLOVER_RULE_EFFECTIVE_UTC)
        self.assertEqual(effective, datetime(2026, 11, 5, tzinfo=timezone.utc))
        self.assertGreater(effective, datetime.fromisoformat(observation_ledger.ROLLOVER_RULE_DECIDED_UTC))

    def test_official_count_start_is_the_wp13_deploy_and_cli_alias_resolves_it(self):
        import json, tempfile
        from pathlib import Path
        self.assertEqual(observation_ledger.STAGE0_COUNT_SINCE_UTC, "2026-11-03T15:18:14+00:00")
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(Path(tmp) / "context.sqlite3")
            observation_ledger.setup(db)
            db.commit()
            db.close()
            out = Path(tmp) / "r.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--state-dir", tmp, "--since", "official", "--output", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())["since_utc"], "2026-11-03T15:18:14+00:00")
