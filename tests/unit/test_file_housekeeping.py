import json
import os
from pathlib import Path
import tempfile
import unittest

from katarina.intelligence.file_housekeeping import organize, restore


class FileHousekeepingTests(unittest.TestCase):
    def test_moves_only_staging_and_undo_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inbox=root/'housekeeping'/'inbox';inbox.mkdir(parents=True)
            data=b'actual persisted report\n'
            (inbox/'report.txt').write_bytes(data)
            (root/'active-report.txt').write_bytes(data)
            for name in ('ticks.json','memory.md','config.json','store.sqlite3','program.py'):
                (inbox/name).write_bytes(data)
            r=organize(root,now=2000000000)
            self.assertEqual(r['moved'],1);self.assertEqual(r['protected'],5)
            self.assertTrue((root/'active-report.txt').exists())
            records=[json.loads(s) for s in (inbox.parent/'moves.jsonl').read_text().splitlines()]
            self.assertEqual([r['state'] for r in records],['INTENT','MOVED'])
            self.assertEqual(restore(root,records[-1]['id']).read_bytes(),data)

    def test_recent_files_and_links_are_untouched(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as other:
            root=Path(d);inbox=root/'housekeeping'/'inbox';inbox.mkdir(parents=True)
            (inbox/'new.log').write_text('writing')
            (Path(other)/'external.txt').write_text('outside')
            (inbox/'link.txt').symlink_to(Path(other)/'external.txt')
            r=organize(root)
            self.assertEqual(r['moved'],0);self.assertEqual(r['deferred'],1);self.assertEqual(r['protected'],1)
            self.assertEqual((Path(other)/'external.txt').read_text(),'outside')

    def test_rejects_junction_target_and_changed_restore(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as other:
            root=Path(d);inbox=root/'housekeeping'/'inbox';inbox.mkdir(parents=True)
            (inbox.parent/'reports').symlink_to(other,target_is_directory=True)
            (inbox/'report.txt').write_text('evidence')
            self.assertEqual(organize(root,now=2000000000)['errors'],1)
            self.assertTrue((inbox/'report.txt').exists())

    def test_bounded_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inbox=root/'housekeeping'/'inbox';inbox.mkdir(parents=True)
            for i in range(30):(inbox/f'{i}.txt').write_text(str(i))
            r=organize(root,now=2000000000,limit=3)
            self.assertEqual(r['checked'],3);self.assertEqual(r['moved'],3)

    def test_changed_or_conflicting_restore_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inbox=root/'housekeeping'/'inbox';inbox.mkdir(parents=True)
            (inbox/'report.txt').write_text('original')
            organize(root,now=2000000000)
            records=[json.loads(s) for s in (inbox.parent/'moves.jsonl').read_text().splitlines()]
            moved=records[-1];target=inbox.parent/moved['destination']
            target.write_text('changed')
            with self.assertRaises(ValueError):restore(root,moved['id'])
            self.assertEqual(target.read_text(),'changed')
            target.write_text('original');(inbox/'report.txt').write_text('new')
            with self.assertRaises(ValueError):restore(root,moved['id'])
            self.assertEqual((inbox/'report.txt').read_text(),'new')
