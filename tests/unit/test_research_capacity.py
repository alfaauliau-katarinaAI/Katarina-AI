from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from katarina.intelligence.research_capacity import research_capacity,MIN_FREE,MAX_DATABASE,WRITE_RESERVE

class ResearchCapacityTests(unittest.TestCase):
    def test_resumes_above_old_cap_only_with_disk_reserve(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'experiment-jobs.sqlite3'
            with p.open('wb') as f:f.truncate(300*1024**2)
            result=research_capacity(d,disk_usage=lambda _:SimpleNamespace(free=3*1024**3))
            self.assertEqual(result['status'],'READY')
            self.assertEqual(research_capacity(d,disk_usage=lambda _:SimpleNamespace(free=MIN_FREE))['status'],'PAUSED_LOW_DISK')
    def test_includes_wal_in_budget(self):
        with tempfile.TemporaryDirectory() as d:
            for name,size in [('experiment-jobs.sqlite3',MAX_DATABASE-WRITE_RESERVE),('experiment-jobs.sqlite3-wal',1)]:
                with (Path(d)/name).open('wb') as f:f.truncate(size)
            self.assertEqual(research_capacity(d,disk_usage=lambda _:SimpleNamespace(free=4*1024**3))['status'],'PAUSED_STORAGE_BUDGET')
