import gzip,hashlib,importlib.util,json,os
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('archive',Path(__file__).parents[2]/'scripts/ai/hf_archive_sync.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class FakeHub:
    def __init__(self,corrupt=False,mutate=None):
        self.objects={};self.corrupt=corrupt;self.mutate=mutate
    def upload(self,local,name):
        self.objects[name]=Path(local).read_bytes()
        return 'a'*40
    def download(self,name,revision,cache):
        cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);p=cache/'object'
        data=self.objects[name]
        if self.corrupt and name.startswith('objects/'):data=b'corrupt'
        p.write_bytes(data)
        if self.mutate and name.startswith('objects/'):self.mutate.write_bytes(b'new source content')
        return p
class ArchiveTests(unittest.TestCase):
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
if __name__=='__main__':unittest.main()
