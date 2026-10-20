import gzip,hashlib,importlib.util,json,os
from pathlib import Path
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
import unittest
spec=importlib.util.spec_from_file_location('archive',Path(__file__).parents[2]/'scripts/ai/hf_archive_sync.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class FakeHub:
    def __init__(self,corrupt=False,mutate=None):
        self.objects={};self.corrupt=corrupt;self.mutate=mutate
    def upload(self,local,name):
        self.objects[name]=Path(local).read_bytes() if isinstance(local,(str,Path)) else local.read()
        return 'a'*40
    def download_memory(self,name,revision):
        data=self.objects[name]
        if self.corrupt and name.startswith('objects/'):return b'corrupt'
        if self.mutate and name.startswith('objects/'):self.mutate.write_bytes(b'new source content')
        return data
    def download(self,name,revision,cache):
        cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);p=cache/'object'
        data=self.objects[name]
        if self.corrupt and name.startswith('objects/'):data=b'corrupt'
        p.write_bytes(data)
        if self.mutate and name.startswith('objects/'):self.mutate.write_bytes(b'new source content')
        return p
class ArchiveTests(unittest.TestCase):
    def setUp(self):
        disk=patch.object(mod.shutil,'disk_usage',return_value=SimpleNamespace(free=10*1024**3))
        disk.start();self.addCleanup(disk.stop)
    def fixture(self,d):
        d=Path(d);p=d/'sample.jsonl';p.write_bytes(b'{"synthetic":true}\n'*500)
        os.utime(p,(1000000000,1000000000))
        return p,d/'ledger',d/'work'
    def test_private_archive_eviction_and_exact_restore(self):
        with tempfile.TemporaryDirectory() as d:
            p,l,w=self.fixture(d);original=p.read_bytes();h=FakeHub()
            r=mod.archive_file(p,h,l,w,evict=True,allowed_cold=[p])
            self.assertTrue(r['restore_verified']);self.assertFalse(p.exists())
            m=json.loads(next(l.glob('*.json')).read_text())
            self.assertTrue(m['evicted']);self.assertTrue(p.with_name(p.name+'.hf-cloud.json').is_file())
            mod.restore_file(m,h,p);self.assertEqual(p.read_bytes(),original)
            # Second worker reuses the already verified local file.
            self.assertEqual(mod.restore_file(m,h,p),p)
            cached=mod.archive_file(p,h,l,w,evict=True,allowed_cold=[p])
            self.assertEqual(cached['status'],'RESTORED_CACHE_PROTECTED');self.assertTrue(p.exists())
    def test_corrupt_download_never_evicts(self):
        with tempfile.TemporaryDirectory() as d:
            p,l,w=self.fixture(d);original=p.read_bytes()
            with self.assertRaises(RuntimeError):
                mod.archive_file(p,FakeHub(corrupt=True),l,w,evict=True,allowed_cold=[p])
            self.assertEqual(p.read_bytes(),original);self.assertFalse(list(l.glob('*.json')))
    def test_changed_source_never_evicts(self):
        with tempfile.TemporaryDirectory() as d:
            p,l,w=self.fixture(d)
            with self.assertRaises(RuntimeError):
                mod.archive_file(p,FakeHub(mutate=p),l,w,evict=True,allowed_cold=[p])
            self.assertTrue(p.exists());self.assertEqual(p.read_bytes(),b'new source content')
    def test_evict_requires_explicit_cold_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            p,l,w=self.fixture(d)
            with self.assertRaises(RuntimeError):mod.archive_file(p,FakeHub(),l,w,evict=True)
            self.assertTrue(p.exists())
            os.utime(p,None)
            with self.assertRaises(RuntimeError):mod.archive_file(p,FakeHub(),l,w,evict=True,allowed_cold=[p])
    def test_restore_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p,l,w=self.fixture(d);h=FakeHub()
            mod.archive_file(p,h,l,w)
            m=json.loads(next(l.glob('*.json')).read_text());p.write_bytes(b'keep me')
            with self.assertRaises(RuntimeError):mod.restore_file(m,h,p)
            self.assertEqual(p.read_bytes(),b'keep me')
    def test_low_disk_bootstrap_verifies_and_restores_without_disk_staging(self):
        with tempfile.TemporaryDirectory() as d:
            p,l,w=self.fixture(d);original=p.read_bytes();h=FakeHub()
            with patch.object(mod.shutil,'disk_usage',return_value=SimpleNamespace(free=mod.RESERVE-100)):
                result=mod.archive_file(p,h,l,w,evict=True,allowed_cold=[p])
            self.assertTrue(result['memory_bootstrap']);self.assertFalse(p.exists())
            manifest=json.loads(next(l.glob('*.json')).read_text())
            mod.restore_file(manifest,h,p);self.assertEqual(p.read_bytes(),original)
    def test_low_disk_bootstrap_rejects_corrupt_remote(self):
        with tempfile.TemporaryDirectory() as d:
            p,l,w=self.fixture(d);original=p.read_bytes()
            with patch.object(mod.shutil,'disk_usage',return_value=SimpleNamespace(free=mod.RESERVE-100)):
                with self.assertRaises(RuntimeError):
                    mod.archive_file(p,FakeHub(corrupt=True),l,w,evict=True,allowed_cold=[p])
            self.assertEqual(p.read_bytes(),original)
    def test_low_disk_does_not_stage_unapproved_live_source(self):
        with tempfile.TemporaryDirectory() as d:
            p,l,w=self.fixture(d);original=p.read_bytes()
            with patch.object(mod.shutil,'disk_usage',return_value=SimpleNamespace(free=mod.RESERVE-100)):
                with self.assertRaises(RuntimeError):mod.archive_file(p,FakeHub(),l,w)
            self.assertEqual(p.read_bytes(),original)
    def test_mutable_json_is_archived_as_a_stable_captured_version(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);p=d/'status.json';p.write_bytes(b'{"version":1}')
            work=d/'work';work.mkdir();hub=FakeHub()
            with mod.capture_json_file(p,work) as snapshot:
                p.write_bytes(b'{"version":2}')
                mod.archive_file(snapshot,hub,d/'ledger',work)
            manifest=json.loads(next((d/'ledger').glob('*.json')).read_text())
            mod.restore_file(manifest,hub,d/'restored.json')
            self.assertEqual((d/'restored.json').read_bytes(),b'{"version":1}')
            self.assertEqual(p.read_bytes(),b'{"version":2}')
    def test_json_capture_retries_a_transient_atomic_rename_gap(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)
            with patch.object(Path,'read_bytes',side_effect=[FileNotFoundError(),b'{"valid":true}']),patch.object(mod.time,'sleep'):
                with mod.capture_json_file(work/'status.json',work) as snapshot:
                    self.assertEqual(snapshot.stat().st_size,len(b'{"valid":true}'))
if __name__=='__main__':unittest.main()

