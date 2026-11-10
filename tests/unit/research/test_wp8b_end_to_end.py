"""WP8b end-to-end offline *synthetic fixture*; NEVER real broker data evidence."""
import csv
import gzip
import hashlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.research.dev_dataset import CSV_FIELDS, DEV_CUTOFF_UTC, load_dev_dataset
from katarina.research.validation import (
    CostModel, DataSplit, HoldoutVault, HypothesisRegistry, Trade, ValidationError,
    canonical, evaluate_development, sha256_text,
)
from scripts.research.simulate_setups import main as simulate_cli
from scripts.research.compare_setups import compare_reports
from scripts.research.register_setup_hypothesis import register_setup

ZERO=datetime(2026,1,5,tzinfo=timezone.utc)


def row(at, minutes, o, h, l, c):
    return {"time_utc":at.isoformat(), "open":o, "high":h, "low":l,
            "close":c, "tick_volume":1, "spread":3, "real_volume":0,
            "closed_at_utc":(at+timedelta(minutes=minutes)).isoformat()}


def synthetic_bars():
    h1=[row(ZERO-timedelta(hours=4-i),60,x,x+2,x-2,x)
        for i,x in enumerate([100,101,102,103])]
    raw=[(101,102,100,101),(102,103,101,102),(103,104,102,103),
         (104.5,106,104.1,105.5),(105.2,106,104,105.8),
         (105.8,117,99.5,107),(107,108,106,107)]
    m5=[row(ZERO+timedelta(minutes=i*5),5,*x) for i,x in enumerate(raw)]
    return {"M5":m5,"H1":h1,"M15":[],"H4":[]}


def frozen_fixture(root, *, clock=True, bad_hash=False):
    """Test-only mock of verified archive SHAPE; evidence is explicitly synthetic."""
    root.mkdir(parents=True,exist_ok=True)
    payload={"schema_version":1,"stage":"WP8A_DEVELOPMENT_ONLY",
             "development_start":(ZERO-timedelta(hours=4)).isoformat(),
             "development_end":(ZERO+timedelta(hours=1)).isoformat(),
             "cutoff_utc":DEV_CUTOFF_UTC.isoformat(),
             "symbols":["XAUUSD"],"files":{},"live_execution_authorized":False}
    for tf, rows in synthetic_bars().items():
        path=root/"XAUUSD"/(tf+".csv.gz")
        path.parent.mkdir(parents=True,exist_ok=True)
        buffer=io.BytesIO()
        with gzip.GzipFile(fileobj=buffer,mode="wb",filename="",mtime=0) as raw:
            with io.TextIOWrapper(raw,encoding="ascii",newline="") as stream:
                writer=csv.writer(stream,lineterminator="\n")
                writer.writerow(CSV_FIELDS)
                for r in rows:
                    writer.writerow([r[k] for k in CSV_FIELDS])
        data=buffer.getvalue()
        path.write_bytes(data)
        proof=[{"time_basis":"INDEPENDENT_UTC","shift_hours":0,
                "source_sha256":"a"*64}] if clock else []
        key="XAUUSD/"+tf+".csv.gz"
        payload["files"][key]={
            "symbol":"XAUUSD","timeframe":tf,"bars":len(rows),
            "first_utc":rows[0]["time_utc"] if rows else None,
            "last_utc":rows[-1]["time_utc"] if rows else None,
            "gaps":[],"clock_evidence":proof,"sha256":hashlib.sha256(data).hexdigest(),
            "bytes":len(data),"point":.01,"trade_tick_size":.01,"trade_contract_size":100.0}
    if bad_hash:
        payload["files"]["XAUUSD/M5.csv.gz"]["sha256"]="0"*64
    payload["manifest_sha256"]=sha256_text(canonical(payload))
    (root/"manifest.json").write_text(canonical(payload)+"\n",encoding="utf-8")
    return payload


def hypothesis():
    return {"name":"TEST DATA ONLY, NOT MARKET EVIDENCE",
            "symbol":"XAUUSD","side":"BUY","regime":"ANY",
            "playbook":"market_structure","rules":"synthetic test",
            "parameters":{"lookback":3,"trend_lookback":3,"target_rr":2.0,
                          "min_rr":1.5,"stop_buffer":.1,
                          "breakout_buffer":.2,"max_hold_bars":3}}


class WP8bEndToEndSynthetic(unittest.TestCase):
    def test_registered_dataset_simulator_validator_comparator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"source"
            evidence=frozen_fixture(source)
            workspace=root/"work"
            workspace.mkdir()
            registry=HypothesisRegistry(workspace/"registry.jsonl")
            entry=register_setup(registry,hypothesis(),registered_utc=ZERO-timedelta(days=1))
            out=root/"trades.jsonl"
            self.assertEqual(simulate_cli(["--dataset",str(source),"--workspace",str(workspace),
                                           "--hypothesis",entry["hypothesis_id"],
                                           "--out",str(out)]),0)
            trades=[Trade.from_dict(json.loads(t)) for t in out.read_text().splitlines()]
            self.assertEqual(len(trades),1)
            split=DataSplit(ZERO-timedelta(days=1),DEV_CUTOFF_UTC,DEV_CUTOFF_UTC,
                            datetime(2027,5,1,tzinfo=timezone.utc))
            costs=CostModel(slippage_per_side=.01,commission_round_trip=.02)
            vault=HoldoutVault(trades,split,registry,workspace/"holdout-openings.jsonl")
            report=evaluate_development(vault,entry["hypothesis_id"],
                                        costs=costs,as_of=datetime(2026,11,2,tzinfo=timezone.utc))
            self.assertEqual(report["period"],"DEVELOPMENT")
            self.assertEqual(report["statistics"]["trades"],1)
            self.assertEqual(report["rejected_trades"],[])
            comparison=compare_reports([report])
            self.assertEqual(comparison["rows"][0]["trades"],1)
            self.assertEqual(comparison["rows"][0]["side"],"BUY")
            self.assertFalse(comparison["live_execution_authorized"])
            self.assertFalse((workspace/"holdout-openings.jsonl").exists())

    def test_bad_archive_hash_and_missing_clock_evidence_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            frozen_fixture(root/"bad-hash",bad_hash=True)
            with self.assertRaisesRegex(ValidationError,"file_hash_mismatch"):
                load_dev_dataset(root/"bad-hash")
            frozen_fixture(root/"no-clock",clock=False)
            with self.assertRaisesRegex(ValidationError,"BROKER_BAR_CLOCK_NOT_VERIFIED"):
                load_dev_dataset(root/"no-clock")


if __name__=="__main__":
    unittest.main()
