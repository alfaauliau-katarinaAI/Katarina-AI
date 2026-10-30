"""Build a source-only PC kit from a committed revision, never private runtime files."""
from pathlib import Path
import argparse
from hashlib import sha256
import io
import json
import subprocess
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
TOP_FILES={'katarina_pc.py','START_KATARINA.bat','SETUP_KATARINA.bat',
           'requirements-pc.txt','requirements-stage07.txt','README.md'}
EXTRA_FILES={'scripts/pc/bind_portable_runtime.py','scripts/pc/manage_owner_access.py','scripts/pc/run_system_acceptance.py',
             'scripts/pc/synthetic_clock_fixture.py',
             'docs/architecture/KATARINA_FULL_SYSTEM_TEST.md','scripts/pc/run_assistant.py','scripts/pc/run_pretrial_acceptance.py',
             'scripts/pc/run_owner_research.py',
             'docs/architecture/KATARINA_MEETING_TARGET_20261016.md',
             'docs/architecture/KATARINA_AI_TRADING_PRETRIAL.md','scripts/pc/environment_recovery.py','scripts/pc/run_pc_acceptance.py','scripts/ai/run_contextual_market_observer.py',
             'scripts/ai/run_readonly_sensor_bridge.py','docs/QUICKSTART_PC.md',
             'docs/architecture/KATARINA_AUTOMATIC_CONNECTION.md',
             'docs/architecture/KATARINA_PORTABLE_HOST.md',
             'docs/architecture/KATARINA_ENVIRONMENT_RECOVERY.md'}


def build(output):
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
    missing=(TOP_FILES|EXTRA_FILES)-set(files)
    if missing:
        raise RuntimeError('committed_pc_kit_files_missing:'+','.join(sorted(missing)))
    manifest={'schema_version':1,'source_commit':revision,'source_tree':tree,
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
    args=parser.parse_args()
    build(args.output)
