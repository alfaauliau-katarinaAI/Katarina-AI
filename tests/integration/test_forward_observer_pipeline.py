import json
import runpy
import tempfile
import unittest
from pathlib import Path
from katarina.intelligence.news.public_context import ContextStore
from katarina.intelligence.perception.screening import save_observation
from katarina.intelligence.demo.forward_outcomes import ForwardOutcomes
from tests.unit.intelligence.test_forward_outcomes import observation

class ForwardPipelineTests(unittest.TestCase):
    def test_saved_observation_links_and_read_only_report(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ContextStore(Path(directory)/"brain.sqlite3")
            engine = ForwardOutcomes(store.db)
            for offset in (0, 300):
                result = observation(offset)
                result["symbols"][0]["regime_detail"] = "TREND_UP"
                if offset == 0:
                    result["symbols"][0]["shadow_hypotheses"] = [dict(
                        family="trend_impulse_break_v1", side="BUY",
                        research_only=True, live_risk_authorized=False)]
                else:
                    result["symbols"][0]["shadow_hypotheses"] = []
                result["decision"] = "NO_TRADE"
                oid = save_observation(store, result)
                engine.process(oid, result)
            query = """SELECT COUNT(*) FROM forward_markouts m
                JOIN brain_observations e ON e.id=m.observation_id
                JOIN brain_observations x ON x.id=m.exit_observation_id
                WHERE m.status='OBSERVED'"""
            self.assertEqual(store.db.execute(query).fetchone()[0], 2)
            report = runpy.run_path(str(Path(__file__).resolve().parents[2]/
                "scripts/ai/report_forward_outcomes.py"))["report"]
            result = report(store.db)
            measured = [g for g in result["groups"] if g["observed"]]
            self.assertEqual(len(measured), 2)
            for group in measured:
                self.assertAlmostEqual(group["spread_markout_bps_mean"], -10000/100.5)
                self.assertFalse(group["context_ready"])
                self.assertEqual(group["regime_detail"], "TREND_UP")
                self.assertEqual(group["shadow_family"],
                    "trend_impulse_break_v1" if group["side"] == "BUY" else "NONE")
            json.dumps(result, allow_nan=False)
            store.db.close()

    def test_restart_preserves_pending_and_does_not_relabel(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"brain.sqlite3"
            store = ContextStore(path)
            ForwardOutcomes(store.db).process(1, observation())
            store.db.close()
            store = ContextStore(path)
            engine = ForwardOutcomes(store.db)
            engine.process(2, observation(300))
            before = store.db.execute(
                "SELECT markout_bps FROM forward_markouts WHERE status='OBSERVED'"
            ).fetchall()
            engine.process(3, observation(330, 150, 151))
            after = store.db.execute(
                "SELECT markout_bps FROM forward_markouts WHERE status='OBSERVED'"
            ).fetchall()
            self.assertEqual(before, after)
            store.db.close()

if __name__ == "__main__":
    unittest.main()
