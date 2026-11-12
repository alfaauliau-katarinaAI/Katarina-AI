"""Build a source-only PC kit with explicit working-tree opt-in and file hashes."""
from pathlib import Path
import argparse
from hashlib import sha256
import io
import json
import subprocess
import sys
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
TOP_FILES={'katarina_pc.py','START_KATARINA.bat','SETUP_KATARINA.bat',
           'requirements-pc.txt','requirements-stage07.txt','requirements-brain-observer.txt','README.md'}
EXTRA_FILES={'scripts/pc/bind_portable_runtime.py','scripts/pc/manage_owner_access.py','scripts/pc/run_system_acceptance.py',
             'scripts/ai/run_independent_demo_worker.py','scripts/deployment/release_manifest.py',
             'docs/MT5_UNIVERSAL_EXECUTION.md',
             'scripts/pc/synthetic_clock_fixture.py',
             'docs/architecture/KATARINA_FULL_SYSTEM_TEST.md','scripts/pc/run_assistant.py','scripts/pc/run_pretrial_acceptance.py',
             'scripts/pc/run_owner_research.py',
             'docs/architecture/KATARINA_MEETING_TARGET_20261016.md',
             'docs/architecture/KATARINA_AI_TRADING_PRETRIAL.md','scripts/pc/environment_recovery.py','scripts/pc/run_pc_acceptance.py','scripts/ai/run_contextual_market_observer.py',
             'scripts/ai/run_readonly_sensor_bridge.py','docs/QUICKSTART_PC.md',
             'docs/architecture/KATARINA_AUTOMATIC_CONNECTION.md',
             'docs/architecture/KATARINA_PORTABLE_HOST.md',
             'docs/architecture/KATARINA_ENVIRONMENT_RECOVERY.md'}


def build(output, *, working_tree=False):
    dirty = bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    if dirty and not working_tree:
        raise RuntimeError('uncommitted_changes_would_be_omitted:use_--working-tree_or_commit_reviewed_changes')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip()
    raw=subprocess.check_output(['git','archive','--format=tar',revision],cwd=ROOT)
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    files={}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive:
            name=member.name
            if member.isfile() and (name in TOP_FILES or name in EXTRA_FILES or name.startswith(('src/','config/'))):
                files[name]=archive.extractfile(member).read()
    if working_tree:
        # Only existing archive paths, explicit kit files and Python source additions.
        # Untracked configuration, runtime state and credentials are never discovered.
        names = set(files) | TOP_FILES | EXTRA_FILES
        promotion = ROOT/'config/promotion_lock.json'
        reviewed_config = set()
        if promotion.is_file():
            sys.path.insert(0, str(ROOT/'src'))
            from katarina.governance.promotion_gate import check, load_json
            if check(ROOT):
                raise ValueError('promotion_gate_not_passed')
            record_path = load_json(promotion)['promotion_record']
            record = load_json(ROOT/record_path)
            names.add(record_path)
            if record.get('validation', {}).get('report'):
                names.add(record['validation']['report'])
            reviewed_config.add('config/promotion_lock.json')
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'src/katarina').rglob('*.py')
                     if '__pycache__' not in p.parts)
        current = {}
        for name in sorted(names):
            path = ROOT/name
            if not path.exists():continue
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError('unsafe_package_path:'+name)
            raw = path.read_bytes()
            if name.startswith('config/') and raw != files.get(name) and name not in reviewed_config:
                raise ValueError('uncommitted_configuration_requires_review:'+name)
            current[name] = raw
        files = current
    missing=(TOP_FILES|EXTRA_FILES)-set(files)
    if missing:
        raise RuntimeError('pc_kit_files_missing:'+','.join(sorted(missing)))
    manifest={'schema_version':1,'source_commit':revision,'source_tree':tree,
              'working_tree_snapshot':working_tree,'source_clean':not dirty,
              'scope':'SOURCE_ONLY_NO_PYTHON_NO_CREDENTIALS','live_authorized':False,
              'files':{name:sha256(content).hexdigest() for name,content in sorted(files.items())}}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,content in sorted(files.items()):
            archive.writestr('Katarina-PC-Test/'+name,content)
        archive.writestr('Katarina-PC-Test/SOURCE_REVISION.json',json.dumps(manifest,indent=2))
    print('PC_TEST_PACKAGE',output,'source',revision,'files',len(files))
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(ROOT/'dist/Katarina-PC-Test.zip'))
    parser.add_argument('--working-tree',action='store_true',help='Explicitly include reviewed local source changes; file hashes identify the snapshot')
    args=parser.parse_args()
    build(args.output,working_tree=args.working_tree)
