"""Isolated autonomous research smoke: sensor pressure -> pause -> resume -> report.

Synthetic price bars and shortened sleep are strictly test fixtures, not broker
data or proof of profitable trading. No MT5, network, order or production state.
"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from katarina.intelligence.lab.adaptive_runtime import (
    AdaptiveResearchLimiter, ResourceSnapshot,
)
from katarina.intelligence.lab.autonomous_research import ResearchPool, ResearchWorker, GRID
from katarina.intelligence.lab.continuous_research_lab import setup
from katarina.intelligence.lab.research_reports import publish_reports
from katarina.monitoring.activity_trace import ActivityTrace

GiB = 1024 ** 3
MiB = 1024 ** 2


class AdaptiveAutonomousSmokeTests(unittest.TestCase):
    def test_paused_worker_resumes_writes_report_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with closing(sqlite3.connect(root / "context.sqlite3")) as db, db:
                setup(db)
                db.execute("INSERT INTO lab_universe(symbol) VALUES('SYNTHETIC')")
                bars = [
                    ("SYNTHETIC", i * 3600 + 3600, 100 + .1 * i,
                     101 + .1 * i, 99 + .1 * i, 100.2 + .1 * i)
                    for i in range(700)
                ]
                db.executemany("INSERT INTO lab_bars VALUES(?,?,?,?,?,?)", bars)
                db.execute("INSERT INTO lab_runs VALUES(?,?,?,?,?)",
                           ("fixture", "SYNTHETIC", "2026-01-01",
                            "synthetic-hash", json.dumps({
                                "spread_proxy_price": .01,
                                "spread_source": "SYNTHETIC_TEST_ONLY",
                            })))
            now = [0.]
            available = [200 * MiB]
            def measure(_):
                return ResourceSnapshot(2, 2 * GiB, available[0], 4 * GiB, .1)
            limiter = AdaptiveResearchLimiter(
                root, measure=measure, clock=lambda: now[0], refresh_seconds=.1)
            trace = ActivityTrace(root)
            worker = ResearchWorker(root, trace, limiter=limiter)
            # Only shorten *test waiting*. Production pacing remains unchanged.
            original_wait = worker.stop.wait
            worker.stop.wait = lambda delay: original_wait(min(delay, .03))
            with patch("katarina.intelligence.lab.autonomous_research.GRID", GRID[:1]), \
                 patch("katarina.intelligence.lab.research_capacity.research_capacity",
                       return_value={"status": "READY"}):
                worker.start()
                try:
                    deadline = time.monotonic() + 5
                    while worker.state["status"] == "STARTING" and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertEqual(worker.state["status"], "PAUSED_MEMORY_PRESSURE")
                    self.assertFalse((root / "experiment-jobs.sqlite3").exists())
                    available[0] = 1200 * MiB
                    now[0] = 1.
                    while worker.state["status"] != "EXPERIMENT_COMPLETED" and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertEqual(worker.state["status"], "EXPERIMENT_COMPLETED",
                                     worker.state)
                finally:
                    worker.close()

                with closing(sqlite3.connect(root / "experiment-jobs.sqlite3")) as db:
                    trial_count = db.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
                    result = json.loads(db.execute("SELECT result_json FROM trials").fetchone()[0])
                self.assertEqual(trial_count, 1)
                self.assertFalse(result["live_authorized"])
                self.assertFalse(result["independent_holdout"])
                self.assertEqual(result["spread_source"], "SYNTHETIC_TEST_ONLY")
                pool = ResearchPool(root, trace, limiter=limiter)
                emitted = pool._within_resource_budget(
                    lambda: publish_reports(root, trace))
                self.assertEqual(emitted, 1)
                with closing(sqlite3.connect(root / "experiment-jobs.sqlite3")) as db:
                    report = json.loads(db.execute(
                        "SELECT report_json FROM research_reports").fetchone()[0])
                self.assertFalse(report["production_approved"])
                self.assertFalse(report["live_authorized"])
                self.assertIn(report["decision"], (
                    "REJECTED", "INSUFFICIENT_EVIDENCE", "AWAITING_COST_REVIEWS",
                    "REVIEW_BLOCKED", "CANDIDATE_FORWARD"))

                # Same cached experiment and same configuration never produces
                # a duplicate, even when a new worker process continues later.
                resumed = ResearchWorker(root, trace, limiter=limiter)
                self.assertFalse(resumed.tick())
                with closing(sqlite3.connect(root / "experiment-jobs.sqlite3")) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM trials").fetchone()[0], 1)
            self.assertEqual(limiter.telemetry()["active_jobs"], 0)
            self.assertFalse((root / "continuous.stop").exists())
            self.assertFalse((root / "orders.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
