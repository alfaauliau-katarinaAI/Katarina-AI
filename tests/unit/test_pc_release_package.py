"""A release must contain audited local source, never silently the previous commit."""
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('pc_package', Path(__file__).resolve().parents[2]/'scripts/pc/build_pc_test_package.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PcReleasePackageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.archive = io.BytesIO()
        with tarfile.open(fileobj=self.archive, mode='w') as tar:
            for name, raw in {'src/katarina/old.py': b'old = True\n', 'config/safe.json': b'{}\n'}.items():
                member = tarfile.TarInfo(name);member.size = len(raw)
                tar.addfile(member, io.BytesIO(raw))
                path = self.root/name;path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(raw)
        for name, value in [('ROOT', self.root), ('TOP_FILES', set()), ('EXTRA_FILES', set())]:
            p = patch.object(package, name, value);p.start();self.addCleanup(p.stop)
        def git(args, **kwargs):
            if args[1] == 'status':return ' M src/katarina/old.py\n'
            if args[1] == 'archive':return self.archive.getvalue()
            return 'revision\n'
        p = patch.object(package.subprocess, 'check_output', side_effect=git);p.start();self.addCleanup(p.stop)

    def test_default_rejects_uncommitted_release(self):
        with self.assertRaisesRegex(RuntimeError, 'uncommitted_changes_would_be_omitted'):
            package.build(self.root/'kit.zip')
        self.assertFalse((self.root/'kit.zip').exists())

    def test_explicit_snapshot_includes_changes_and_new_source_but_not_private_config(self):
        # write_bytes: write_text would emit CRLF on Windows while the assertion checks exact packaged bytes.
        (self.root/'src/katarina/old.py').write_bytes(b'new = True\n')
        (self.root/'src/katarina/new.py').write_bytes(b'pass\n')
        (self.root/'config/private.json').write_text('{"token":"never-package"}')
        manifest = package.build(self.root/'kit.zip', working_tree=True)
        self.assertTrue(manifest['working_tree_snapshot'])
        self.assertFalse(manifest['source_clean'])
        with zipfile.ZipFile(self.root/'kit.zip') as archive:
            self.assertEqual(archive.read('Katarina-PC-Test/src/katarina/old.py'), b'new = True\n')
            self.assertIn('Katarina-PC-Test/src/katarina/new.py', archive.namelist())
            self.assertNotIn('Katarina-PC-Test/config/private.json', archive.namelist())

    def test_modified_configuration_is_not_silently_packaged(self):
        (self.root/'config/safe.json').write_text('{"token":"private"}')
        with self.assertRaisesRegex(ValueError, 'uncommitted_configuration_requires_review'):
            package.build(self.root/'kit.zip', working_tree=True)
