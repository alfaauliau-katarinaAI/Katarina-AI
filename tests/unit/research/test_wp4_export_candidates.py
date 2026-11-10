"""WP4 candidate export from hash-verified, pre-cutoff synthetic tick archives."""
import gzip
import hashlib
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.intelligence.operations import candidate_ledger, observation_ledger
from katarina.research.validation import HypothesisRegistry, ValidationError, CostModel
from scripts.research.export_candidates import export_candidates

NOW = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)


def spec():
    return {"name":"SYNTHETIC WP4 TICK TEST", "symbol":"XAUUSD.vx", "side":"BUY",
            "regime":"UPTREND","playbook":"pullback","rules":"synthetic-only",
            "parameters":{"exit_mode":"CANDIDATE_LEVELS_TICK_FIRST_TOUCH",
                          "entry_wait_seconds":30,"max_hold_seconds":120}}


class WP4ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.registry=HypothesisRegistry(self.root/"hypotheses.jsonl")
        self.hid=self.registry.register(spec(),registered_utc=NOW-timedelta(days=1))["hypothesis_id"]
        self.card={"action":"WAIT","market_state":"UPTREND","direction_bias":"BUY",
                   "selected_method":"pullback","technical_setup":"SYNTHETIC",
                   "conditional_side":"BUY","conditional_invalidation":100.0,
                   "conditional_target":104.0,"technical_evidence_score":0.7,
                   "blocking_reasons":["model_not_authorized"],
                   "closed_bar_times_utc":{"M5":(NOW-timedelta(minutes=5)).isoformat()},
                   "broker_spread_price":.2}
        self.cid=observation_ledger.record_snapshot(
            self.db,observed_utc=NOW,clock_shift_hours=0,
            cards={"XAUUSD.vx":self.card},
            quotes={"XAUUSD.vx":(101.9,102.1,NOW.timestamp()-2)})
        candidate_ledger.record(
            self.db,cycle_id=self.cid,cards={"XAUUSD.vx":self.card},
            quotes={"XAUUSD.vx":(101.9,102.1,NOW.timestamp()-2)})
        self.day=NOW.date().isoformat()
        ticks=[
            (int((NOW+timedelta(seconds=1)).timestamp()*1000),101.9,102.1,0),
            (int((NOW+timedelta(seconds=2)).timestamp()*1000),101.95,102.15,0),
            (int((NOW+timedelta(seconds=3)).timestamp()*1000),104.1,104.3,0),
        ]
        raw="time_msc,bid,ask,flags\n"+"".join(f"{ms},{bid},{ask},{flags}\n" for ms,bid,ask,flags in ticks)
        digest=hashlib.sha256(raw.encode("ascii")).hexdigest()
        out=self.root/"broker-ticks"/"XAUUSD.vx"/(self.day+".csv.gz")
        out.parent.mkdir(parents=True)
        with out.open("wb") as output:
            with gzip.GzipFile(filename="",fileobj=output,mode="wb",mtime=0) as archive:
                archive.write(raw.encode("ascii"))
        self.db.execute(
            "INSERT INTO broker_tick_days(symbol,day,status,ticks,sha256,file,server_shift_hours,"
            "snapshots_checked,snapshots_matched) VALUES(?,?,?,?,?,?,?,?,?)",
            ("XAUUSD.vx",self.day,"STORED",3,digest,
             out.relative_to(self.root).as_posix(),0,1,1))
        self.db.commit()

    def test_export_wait_without_order_and_with_costed_tick_spreads(self):
        trades, skipped=export_candidates(self.db,self.root,self.registry,self.hid)
        self.assertEqual(len(trades),1)
        t=trades[0]
        self.assertEqual(t.side,"BUY")
        self.assertEqual(t.entry_at,NOW+timedelta(seconds=1))
        self.assertEqual(t.data_until,NOW-timedelta(minutes=5))
        self.assertEqual(t.exit_at,NOW+timedelta(seconds=3))
        self.assertAlmostEqual(t.entry_mid,102.0)
        self.assertGreater(t.exit_mid,t.entry_mid)
        self.assertAlmostEqual(t.spread_entry,.2)
        self.assertGreater(CostModel(commission_round_trip=.02).cost_r(t),0)
        self.assertEqual(skipped,{})
        self.assertEqual(self.db.execute("SELECT orders_submitted FROM observer_cycles").fetchone()[0],0)

    def test_hash_tamper_rejected(self):
        self.db.execute("UPDATE broker_tick_days SET sha256=?",
                        ("f"*64,))
        self.db.commit()
        with self.assertRaisesRegex(ValidationError,"HASH_MISMATCH"):
            export_candidates(self.db,self.root,self.registry,self.hid)

    def test_clock_unverified_and_reconciliation_unmatched_rejected(self):
        self.db.execute("UPDATE broker_tick_days SET snapshots_matched=0")
        self.db.commit()
        with self.assertRaisesRegex(ValidationError,"CLOCK_OR_RECONCILIATION"):
            export_candidates(self.db,self.root,self.registry,self.hid)

    def test_holdout_candidate_blocked(self):
        self.db.execute("UPDATE research_candidates SET observed_utc='2026-11-02T00:00:00+00:00'")
        self.db.commit()
        with self.assertRaisesRegex(ValidationError,"holdout_data_forbidden"):
            export_candidates(self.db,self.root,self.registry,self.hid)

    def test_registered_exit_rule_required(self):
        with tempfile.TemporaryDirectory() as folder:
            other=HypothesisRegistry(Path(folder)/"registry.jsonl")
            invalid=spec()
            del invalid["parameters"]["max_hold_seconds"]
            key=other.register(invalid,registered_utc=NOW)["hypothesis_id"]
            with self.assertRaisesRegex(ValidationError,"exit_parameter_missing"):
                export_candidates(self.db,self.root,other,key)


if __name__=="__main__":
    unittest.main()
