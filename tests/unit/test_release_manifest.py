import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('release_manifest',Path(__file__).resolve().parents[2]/'scripts/deployment/release_manifest.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ReleaseManifestTests(unittest.TestCase):
    def test_drift_and_missing_and_unrecorded_source_are_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'src/katarina';source.mkdir(parents=True)
            a=source/'first.py';b=source/'second.py';a.write_text('original\n');b.write_text('unchanged\n')
            private=root/'state/token.secret';private.parent.mkdir();private.write_text('PRIVATE')
            manifest=mod.generate(root)
            self.assertEqual(mod.verify(root,manifest)['status'],'MATCH')
            a.write_text('modified\n');b.unlink();(source/'unrecorded.py').write_text('untracked\n')
            report=mod.verify(root,manifest)
            self.assertEqual(report['changed'],['src/katarina/first.py'])
            self.assertEqual(report['missing'],['src/katarina/second.py'])
            self.assertEqual(report['extra'],['src/katarina/unrecorded.py'])
            self.assertNotIn('PRIVATE',str(manifest))
    def test_line_endings_are_distinguished_from_behavior_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'src/katarina/example.py';p.parent.mkdir(parents=True);p.write_bytes(b'pass\n')
            manifest=mod.generate(root);p.write_bytes(b'\xef\xbb\xbfpass\r\n')
            report=mod.verify(root,manifest)
            self.assertEqual(report['status'],'MATCH');self.assertEqual(report['line_endings_only'],['src/katarina/example.py'])
