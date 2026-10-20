"""Provision a portable private archive service. Never accept tokens as CLI arguments."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

DEFAULT_CODE = Path(__file__).resolve().parents[2]

def load_archive(code_root):
    spec=importlib.util.spec_from_file_location('katarina_archive',code_root/'scripts/ai/hf_archive_sync.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def provision(args):
    code=Path(args.code_root).expanduser().resolve()
    manifest=code/'ops/deployment/release-manifest.json'
    if not manifest.is_file():raise RuntimeError('RELEASE_MANIFEST_REQUIRED')
    spec=importlib.util.spec_from_file_location('katarina_release',code/'scripts/deployment/release_manifest.py')
    release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
    if release.verify(code,json.loads(manifest.read_text()))['status']!='MATCH':
        raise RuntimeError('RELEASE_SOURCE_DRIFT')
    requested_base=Path(args.base_dir).expanduser()
    if requested_base.is_symlink():raise RuntimeError('PRIVATE_BASE_SYMLINK_FORBIDDEN')
    base=requested_base.resolve()
    state=Path(args.state_dir).expanduser().resolve()
    if base.is_relative_to(code) or state.is_relative_to(code) or base==state:
        raise RuntimeError('PRIVATE_RUNTIME_MUST_BE_OUTSIDE_CHECKOUT')
    if not re.fullmatch('[a-f0-9]{40}',args.source_commit):
        raise RuntimeError('PINNED_SOURCE_COMMIT_REQUIRED')
    if not 10<=args.interval_minutes<=1440:
        raise RuntimeError('SYNC_INTERVAL_MUST_BE_10_TO_1440_MINUTES')
    base.mkdir(parents=True,exist_ok=True);state.mkdir(parents=True,exist_ok=True)
    if base.is_symlink():raise RuntimeError('PRIVATE_BASE_SYMLINK_FORBIDDEN')
    if os.name=='nt':
        subprocess.run(['icacls',str(base),'/inheritance:r','/grant:r',
                        '*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F'],capture_output=True,check=True)
    else:
        base.chmod(0o700)
    mod=load_archive(code)
    config_path=base/'config.json'
    old=json.loads(config_path.read_text(encoding='utf-8-sig')) if config_path.exists() else {}
    if old.get('repo') and old['repo']!=args.repo_id:
        raise RuntimeError('EXISTING_REPOSITORY_DIFFERS_MIGRATE_SEPARATELY')
    old_state=old.get('state_dir') or next(iter(old.get('backup_databases',[])),None)
    if old_state:
        old_state=Path(old_state) if old.get('state_dir') else Path(old_state).parent
        if old_state.resolve()!=state:raise RuntimeError('EXISTING_CONFIG_STATE_MISMATCH')
    config=dict(old,schema_version=2,base_dir=str(base),state_dir=str(state),repo=args.repo_id,
                expected_account=args.expected_account,token_env=args.token_env,
                interval_minutes=args.interval_minutes,
                cold_files=old.get('cold_files',[]),
                sync_files=old.get('sync_files',[str(state/n) for n in ('research-reports.json','research-growth.json','research-lab.json')]),
                backup_databases=old.get('backup_databases',[str(state/n) for n in ('experiment-jobs.sqlite3','context.sqlite3','cognitive-memory.sqlite3')]))
    if getattr(args,'include_operational_ledgers',False):
        for name in ('calibration.sqlite3','network-doctor.sqlite3','research-soak.sqlite3',
                     'demo-forward/experiment.sqlite3','demo-forward/orders.sqlite3'):
            if str(state/name) not in config['backup_databases']:config['backup_databases'].append(str(state/name))
        config['data_scope']='PRIVATE_RESEARCH_AND_OPERATIONAL_LEDGERS_NO_AUTH_SECRETS'
    if args.client_dir:config['client_dir']=str(Path(args.client_dir).resolve())
    mod.configure_runtime(config)
    for name in config['cold_files']:mod.validate_cold_source(name)
    if args.provision_credential:
        token=os.environ.get(args.token_env,'').strip()
        if not re.fullmatch(r'hf_[A-Za-z0-9]{10,}',token):raise RuntimeError('HF_TOKEN_ENVIRONMENT_REQUIRED')
        destination=base/('token.dpapi' if os.name=='nt' else 'token.secret')
        if destination.exists():
            previous=mod.dpapi(destination.read_bytes(),decrypt=True).decode('ascii') if os.name=='nt' else destination.read_text(encoding='ascii')
            if previous.strip()!=token:raise RuntimeError('EXISTING_CREDENTIAL_DIFFERS_ROTATE_SEPARATELY')
        else:
            payload=mod.dpapi(token.encode('ascii')) if os.name=='nt' else token.encode('ascii')
            fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
    if os.name!='nt':config['token_file']=str(base/'token.secret')
    mod.atomic_json(config_path,config)
    (base/'work').mkdir(exist_ok=True);(base/'manifests').mkdir(exist_ok=True)
    runner=code/'scripts/ai/run_hf_archive_sync.py'
    if not runner.is_file():raise RuntimeError('CANONICAL_RUNNER_MISSING')
    metadata=dict(schema_version=1,source_commit=args.source_commit,code_root=str(code),
                  config=str(config_path),runner=str(runner),python=sys.executable,
                  source_sha256={str(p.relative_to(code)):mod.sha_file(p) for p in
                      [code/'scripts/ai/hf_archive_sync.py',runner,code/'scripts/deployment/install_hf_storage.py']},
                  secrets_in_git=False,live_authorized=False)
    mod.atomic_json(base/'deployment.json',metadata)
    if args.schedule:
        if os.name!='nt':raise RuntimeError('USE_DOCUMENTED_SYSTEMD_TIMER_ON_LINUX')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',args.task_name):raise RuntimeError('INVALID_TASK_NAME')
        command=subprocess.list2cmdline([sys.executable,str(runner),'--config',str(config_path)])
        subprocess.run(['schtasks','/Create','/TN',args.task_name,'/SC','MINUTE','/MO',str(args.interval_minutes),
                        '/RU','SYSTEM','/RL','HIGHEST','/TR',command,'/F'],capture_output=True,check=True)
    if args.verify:
        if args.client_dir:sys.path.insert(0,str(Path(args.client_dir).resolve()))
        import certifi
        os.environ['SSL_CERT_FILE']=certifi.where()
        mod.Hub(mod.load_token(config)) # identity + repository privacy; no upload
    return dict(configured=True,source_commit=args.source_commit,scheduled=args.schedule,
                repo=args.repo_id,credential_provisioned=args.provision_credential,live_authorized=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--code-root',default=str(DEFAULT_CODE));p.add_argument('--base-dir',required=True)
    p.add_argument('--state-dir',required=True);p.add_argument('--repo-id',required=True)
    p.add_argument('--expected-account',required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--client-dir');p.add_argument('--token-env',default='HF_TOKEN')
    p.add_argument('--provision-credential',action='store_true');p.add_argument('--verify',action='store_true')
    p.add_argument('--include-operational-ledgers',action='store_true')
    p.add_argument('--schedule',action='store_true');p.add_argument('--interval-minutes',type=int,default=10)
    p.add_argument('--task-name',default='KatarinaHFResearchArchiveSync')
    print(json.dumps(provision(p.parse_args())),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps(dict(configured=False,error=type(error).__name__)),flush=True)
        raise SystemExit(1) from None
