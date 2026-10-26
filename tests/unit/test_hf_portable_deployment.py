import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
archive=module('portable_archive','scripts/ai/hf_archive_sync.py')
installer=module('portable_installer','scripts/deployment/install_hf_storage.py')
runner=module('portable_runner','scripts/ai/run_hf_archive_sync.py')
catalog=module('portable_catalog','scripts/deployment/recover_hf_catalog.py')

class PortableStorageTests(unittest.TestCase):
    def test_cloud_catalog_can_be_rebuilt_without_the_old_host_or_ledger(self):
        name='manifests/'+'a'*64+'/'+'b'*64+'.json'
        value=dict(repo=archive.REPO,source='old-machine-temporary/context.sqlite3',
                   logical_source='state/context.sqlite3',archived_utc='2026-10-21T00:00:00+00:00',
                   object='objects/cc/'+'c'*64+'.gz',object_revision='d'*40)
        hub=SimpleNamespace(api=SimpleNamespace(repo_info=lambda *a,**k:SimpleNamespace(private=True,sha='e'*40,siblings=[SimpleNamespace(rfilename=name)])),
                            download_memory=Mock(return_value=json.dumps(value).encode()))
        result=catalog.collect(archive,hub)
        self.assertEqual(result['latest']['state/context.sqlite3']['manifest'],value)
        self.assertFalse(result['latest']['state/context.sqlite3']['legacy_mapping_required'])
        hub.download_memory.assert_called_once_with(name,'e'*40)

    def test_public_repository_or_different_account_is_refused(self):
        api=SimpleNamespace(whoami=lambda:{'name':archive.EXPECTED_ACCOUNT},repo_info=lambda *a,**k:SimpleNamespace(private=False))
        with patch.dict(sys.modules,{'huggingface_hub':SimpleNamespace(HfApi=lambda **k:api)}):
            with self.assertRaisesRegex(RuntimeError,'PRIVATE_REPOSITORY_REQUIRED'):archive.Hub('synthetic')
            api.whoami=lambda:{'name':'different-owner'}
            with self.assertRaisesRegex(RuntimeError,'UNEXPECTED_ACCOUNT'):archive.Hub('synthetic')

    def test_config_accepts_a_new_root_and_account_without_legacy_paths(self):
        with tempfile.TemporaryDirectory() as d,patch.multiple(archive,BASE=archive.BASE,STATE=archive.STATE,REPO=archive.REPO,EXPECTED_ACCOUNT=archive.EXPECTED_ACCOUNT):
            archive.configure_runtime(dict(base_dir=str(Path(d)/'vault'),state_dir=str(Path(d)/'observations'),repo='team/new-archive',expected_account='new-owner'))
            self.assertEqual(archive.REPO,'team/new-archive')
            self.assertEqual(archive.EXPECTED_ACCOUNT,'new-owner')
            self.assertEqual(archive.BASE,(Path(d)/'vault').resolve())
            for invalid in ('../escape','user/repo/../../other','https://evil/repo'):
                with self.assertRaisesRegex(RuntimeError,'INVALID_REPOSITORY'):
                    archive.configure_runtime(dict(repo=invalid))

    def test_active_state_credentials_tick_inputs_and_open_sqlite_cannot_be_evicted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);state=root/'state';base=root/'vault';state.mkdir();base.mkdir()
            old=root/'legacy';old.mkdir()
            files=[state/'memory.json',base/'config.json',old/'ticks.npz',old/'connection.private.json',old/'token.json',old/'live.sqlite3']
            (old/'live.sqlite3-wal').touch()
            with patch.object(archive,'BASE',base),patch.object(archive,'STATE',state):
                for p in files:
                    p.write_bytes(b'preserve');os.utime(p,(1000000000,1000000000))
                    with self.subTest(path=p),self.assertRaisesRegex(RuntimeError,'PROTECTED_SOURCE'):
                        archive.archive_file(p,Mock(),base/'ledger',base/'work',evict=True,allowed_cold=[p])
                    self.assertEqual(p.read_bytes(),b'preserve')

    def test_restore_rejects_unpinned_or_traversing_objects_before_network(self):
        hub=Mock()
        value=dict(repo=archive.REPO,object='../../api/whoami',object_revision='main')
        with tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(RuntimeError,'INVALID_PINNED_ARCHIVE_PATH'):
            archive.restore_file(value,hub,Path(d)/'copy')
        hub.download.assert_not_called()

    @unittest.skipIf(os.name=='nt','POSIX file permission semantics')
    def test_destination_secret_requires_private_permissions_and_is_not_copied_from_dpapi(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{},clear=True),patch.object(archive,'BASE',Path(d)):
            p=Path(d)/'token.secret';token='hf_'+'x'*32;p.write_text(token);p.chmod(0o600)
            self.assertEqual(archive.load_token({}),token)
            p.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError,'CREDENTIAL_PERMISSIONS_REQUIRED'):archive.load_token({})

    def test_existing_private_repository_is_not_created_on_every_sync(self):
        api=SimpleNamespace(whoami=lambda:{'name':archive.EXPECTED_ACCOUNT},repo_info=lambda *a,**k:SimpleNamespace(private=True),create_repo=Mock())
        with patch.dict(sys.modules,{'huggingface_hub':SimpleNamespace(HfApi=lambda **k:api)}):
            archive.Hub('synthetic-token')
        api.create_repo.assert_not_called()

    @unittest.skipIf(os.name=='nt','POSIX fresh-machine installation fixture')
    def test_fresh_machine_installs_from_code_and_external_secret_without_old_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);code=root/'different-machine-code';base=root/'private';state=root/'state'
            for name in ('scripts/ai/hf_archive_sync.py','scripts/ai/run_hf_archive_sync.py','scripts/deployment/install_hf_storage.py','scripts/deployment/release_manifest.py'):
                p=code/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
            release=module('fixture_release','scripts/deployment/release_manifest.py')
            manifest=code/'ops/deployment/release-manifest.json';manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps(release.generate(code)))
            args=argparse.Namespace(code_root=str(code),base_dir=str(base),state_dir=str(state),source_commit='a'*40,
                interval_minutes=10,repo_id='other-owner/private-data',expected_account='other-owner',token_env='HF_TOKEN',
                client_dir=None,provision_credential=True,schedule=False,verify=False,task_name='test')
            with patch.dict(os.environ,{'HF_TOKEN':'hf_'+'x'*32},clear=True):
                installer.provision(args);installer.provision(args)
            config=json.loads((base/'config.json').read_text())
            self.assertEqual(config['cold_files'],[])
            self.assertEqual(config['backup_databases'][0],str(state/'experiment-jobs.sqlite3'))
            self.assertNotIn('hf_'+'x'*32,(base/'config.json').read_text()+(base/'deployment.json').read_text())
            self.assertEqual((base/'token.secret').stat().st_mode&0o777,0o600)
            self.assertEqual(base.stat().st_mode&0o777,0o700)
            other=argparse.Namespace(**vars(args));other.state_dir=str(root/'wrong-state')
            with self.assertRaisesRegex(RuntimeError,'EXISTING_CONFIG_STATE_MISMATCH'):installer.provision(other)

    def test_runner_uses_its_neighbor_source_and_explicit_config(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json';p.write_text(json.dumps(dict(base_dir=d)))
            with patch.object(sys,'argv',['runner','--config',str(p)]),patch.object(runner.runpy,'run_path') as run:
                runner.main()
            self.assertEqual(run.call_args.args[0],str(ROOT/'scripts/ai/hf_archive_sync.py'))
            self.assertEqual(run.call_args.kwargs,dict(run_name='__main__'))

    def test_upload_cooldown_does_not_block_a_requested_restore(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);state=base/'runtime';state.mkdir()
            config=base/'config.json';config.write_text(json.dumps(dict(base_dir=str(base),state_dir=str(state))))
            receipt=base/'receipt.json';receipt.write_text('{}')
            archive.atomic_json(base/'cooldown.json',dict(retry_epoch=archive.time.time()+3600))
            with patch.multiple(archive,BASE=archive.BASE,STATE=archive.STATE,REPO=archive.REPO,EXPECTED_ACCOUNT=archive.EXPECTED_ACCOUNT), \
                 patch.object(sys,'argv',['archive','--config',str(config),'--restore-manifest',str(receipt),'--destination',str(base/'restored')]), \
                 patch.dict(sys.modules,{'certifi':SimpleNamespace(where=lambda:'fixture-ca'),'filelock':SimpleNamespace(FileLock=lambda *a,**k:contextlib.nullcontext())}), \
                 patch.object(archive,'load_token',return_value='synthetic'),patch.object(archive,'Hub'),patch.object(archive,'restore_file') as restore,contextlib.redirect_stdout(io.StringIO()):
                archive.main();restore.assert_called_once()

if __name__=='__main__':unittest.main()
