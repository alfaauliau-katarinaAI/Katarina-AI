"""CLI since selection is read-only and rejects ambiguous ISO dates."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from katarina.intelligence.operations import observation_ledger as ledger

SCRIPT=Path(__file__).resolve().parents[2]/'scripts/ai/check_stage0_health.py'


class SinceCLI(unittest.TestCase):
    def test_cli_selects_since_without_modifying_ledger(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);path=root/'context.sqlite3';out=root/'result.json'
            since=datetime(2026,9,1,tzinfo=timezone.utc)
            with closing(sqlite3.connect(path)) as db:
                for when,orders in ((since-timedelta(days=1),1),(since,0)):
                    ledger.close_cycle(db,finished_utc=when,status='NO_MARKET_DATA',
                        reason='NO_QUOTES',orders_submitted=orders)
            before=sha256(path.read_bytes()).hexdigest()
            proc=subprocess.run([sys.executable,str(SCRIPT),'--state-dir',str(root),
                '--since',since.isoformat(),'--output',str(out)],capture_output=True,text=True,timeout=30)
            self.assertEqual(proc.returncode,0,proc.stderr)
            report=json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(report['cycles_total'],1)
            self.assertEqual(report['since_utc'],since.isoformat())
            self.assertEqual(sha256(path.read_bytes()).hexdigest(),before)

    def test_cli_rejects_naive_or_invalid_since_before_reading_database(self):
        for stamp in ('2026-09-01','invalid','2099-01-01T00:00:00Z'):
            with self.subTest(stamp=stamp):
                result=subprocess.run([sys.executable,str(SCRIPT),'--state-dir','unused',
                    '--since',stamp],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,2)
                self.assertIn('--since requires',result.stderr)
