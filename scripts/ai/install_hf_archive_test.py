"""Install committed private archive synchronizer on owner's Windows testing VPS."""
import argparse,base64,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time,urllib.request,ssl
from pathlib import Path
BASE=Path(r'C:\KatarinaDev\config\hf-storage')
ROOT=Path(r'C:\KatarinaGitTest-4e14b098')
STATE=Path(r'C:\KatarinaDev\state\owner-broker-readonly\readonly-observer')
def main():
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--sealed',required=True)
    a=p.parse_args()
    if not re.fullmatch('[a-f0-9]{40}',a.commit):raise RuntimeError('INVALID_COMMIT')
    BASE.mkdir(parents=True,exist_ok=True)
    subprocess.run(['icacls',str(BASE),'/inheritance:r','/grant:r','*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F'],check=True,capture_output=True)
    import certifi
    url='https://raw.githubusercontent.com/alfaauliau-katarinaAI/Katarina-AI/'+a.commit+'/scripts/ai/hf_archive_sync.py'
    with urllib.request.urlopen(url,context=ssl.create_default_context(cafile=certifi.where()),timeout=30) as response:
        source=response.read(100001)
    if len(source)>100000:raise RuntimeError('SOURCE_TOO_LARGE')
    compile(source,url,'exec')
    target=ROOT/'scripts/ai/hf_archive_sync.py';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(source)
    spec=importlib.util.spec_from_file_location('hfarchive',target);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    result=subprocess.run([r'C:\Program Files\Git\usr\bin\openssl.exe','pkeyutl','-decrypt',
        '-inkey',r'C:\KatarinaDev\config\gemini-private\transfer-private.pem',
        '-pkeyopt','rsa_padding_mode:oaep','-pkeyopt','rsa_oaep_md:sha256','-pkeyopt','rsa_mgf1_md:sha256'],
        input=base64.b64decode(a.sealed,validate=True),capture_output=True,timeout=20)
    if result.returncode or not result.stdout.startswith(b'hf_'):raise RuntimeError('CREDENTIAL_UNSEAL_FAILED')
    credential=result.stdout.strip()
    (BASE/'token.dpapi').write_bytes(mod.dpapi(credential))
    if mod.dpapi((BASE/'token.dpapi').read_bytes(),decrypt=True)!=credential:raise RuntimeError('DPAPI_ROUNDTRIP_FAILED')
    sys.path.insert(0,r'C:\KatarinaDev\runtime\hf-client')
    import certifi as hf_certifi
    os.environ['SSL_CERT_FILE']=hf_certifi.where()
    os.environ['HF_HUB_DISABLE_XET']='1'
    hub=mod.Hub(credential.decode('ascii'))
    # Freeze a reviewed, inactive legacy file allowlist; never evict live state or tick inputs.
    prefixes=('Independent','Market','PricePattern','RegimeStrategy','Transition','PairSpecialist','Condition','BiasAudit','NewsPattern','XauFocus','MtfLocked','MT5Parity')
    names={'predictions.jsonl','samples.csv','results.json','trials.json','trades.csv','traces.json',
           'results.partial.json','partial.json','candidate_table.json','analysis.json','summary.json'}
    proc=subprocess.run(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Process | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress'],capture_output=True,text=True,check=True)
    processes=json.loads(proc.stdout or '[]')
    tasks=subprocess.run(['schtasks','/Query','/FO','CSV','/V'],capture_output=True,text=True,check=True).stdout.lower()
    cold=[]
    for r in Path('C:/').iterdir():
        if not r.is_dir() or not r.name.startswith(prefixes):continue
        active=any(x['ProcessId'] not in (os.getpid(),os.getppid()) and str(r).lower() in (x.get('CommandLine') or '').lower() for x in processes)
        if active or str(r).lower() in tasks:continue
        for folder,dirs,files in os.walk(r):
            dirs[:]=[x for x in dirs if x not in ('venv','deps','.git','__pycache__','node_modules')]
            for f in files:
                q=Path(folder)/f
                if f not in names or q.is_symlink():continue
                st=q.stat()
                if st.st_size>=2_000_000 and time.time()-st.st_mtime>86400:cold.append(q)
    # Old standalone QA snapshots, not the live state databases.
    old_roots=[Path(r'C:\KatarinaFreshLab\build-proof'),Path(r'C:\KatarinaDev\artifacts\contextual-observer')]
    for r in old_roots:
        if not r.exists() or str(r).lower() in tasks:continue
        if any(x['ProcessId'] not in (os.getpid(),os.getppid()) and str(r).lower() in (x.get('CommandLine') or '').lower() for x in processes):continue
        for q in r.rglob('*.sqlite3'):
            if q.is_symlink() or Path(str(q)+'-wal').exists():continue
            st=q.stat()
            if st.st_size>=2_000_000 and time.time()-st.st_mtime>86400:cold.append(q)
    cold=sorted(set(cold),key=lambda q:-q.stat().st_size)
    config=dict(schema_version=1,repo=mod.REPO,cold_files=[str(q) for q in cold],
                sync_files=[str(STATE/f) for f in ('research-reports.json','research-growth.json','research-lab.json')],
                backup_databases=[str(STATE/f) for f in ('experiment-jobs.sqlite3','context.sqlite3','cognitive-memory.sqlite3')])
    mod.atomic_json(BASE/'config.json',config)
    work=BASE/'work';work.mkdir(exist_ok=True)
    subprocess.run(['compact.exe','/C','/I','/Q',str(work)],capture_output=True,check=True)
    runner=BASE/'run-hf-sync.py'
    runner_url='https://raw.githubusercontent.com/alfaauliau-katarinaAI/Katarina-AI/'+a.commit+'/scripts/ai/run_hf_archive_sync.py'
    with urllib.request.urlopen(runner_url,context=ssl.create_default_context(cafile=certifi.where()),timeout=30) as response:
        runner_source=response.read(10001)
    if len(runner_source)>10000:raise RuntimeError('RUNNER_TOO_LARGE')
    compile(runner_source,runner_url,'exec')
    runner.write_bytes(runner_source)
    command='"'+sys.executable+'" "'+str(runner)+'"'
    subprocess.run(['schtasks','/Create','/TN','KatarinaHFResearchArchiveSync','/SC','MINUTE','/MO','10','/RU','SYSTEM','/RL','HIGHEST','/TR',command,'/F'],capture_output=True,check=True)
    print(json.dumps(dict(installed=True,repo=mod.REPO,authenticated=True,private=True,
                         cold_files=len(cold),cold_bytes=sum(q.stat().st_size for q in cold),
                         source_commit=a.commit,source_sha256=hashlib.sha256(source).hexdigest(),
                         credential_protected='WINDOWS_DPAPI_AND_ADMIN_SYSTEM_ACL',interval_minutes=10)),flush=True)
    # Start immediately; recurring task continues independently of ChatGPT.
    subprocess.run(['schtasks','/Run','/TN','KatarinaHFResearchArchiveSync'],capture_output=True,check=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps(dict(status='INSTALL_FAILED',error=type(e).__name__)),flush=True)
        raise SystemExit(1) from None
