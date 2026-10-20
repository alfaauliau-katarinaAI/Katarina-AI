"""Extend the private archive allowlist with inactive legacy research results."""
import json,os,subprocess,time
from pathlib import Path
BASE=Path(r'C:\KatarinaDev\config\hf-storage')
PREFIXES=('Independent','Market','PricePattern','RegimeStrategy','Transition','PairSpecialist','Condition','BiasAudit','NewsPattern','XauFocus','MtfLocked','MT5Parity')
NAMES=set('results.json trials.json summary.json candidate_table.json analysis.json direct_results.json all_trials.json m5_results.json event_study.json saturation_results.json audit-before-timestamp-fix.json audit.json audit_results.json validation_candidates.json clean_results.json repair_results.json previous_candidate_audit.json m5_trials.json historical_finalists.json result.json allocation_result.json volume_daily.json trades.json'.split())
def main():
    processes=subprocess.run(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Process | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress'],capture_output=True,text=True,timeout=60,check=True)
    rows=json.loads(processes.stdout or '[]')
    if isinstance(rows,dict):rows=[rows]
    references=[(row.get('CommandLine') or '').casefold() for row in rows if row['ProcessId'] not in (os.getpid(),os.getppid())]
    tasks=subprocess.run(['schtasks','/Query','/FO','CSV','/V'],capture_output=True,text=True,timeout=60,check=True).stdout.casefold()
    config=json.loads((BASE/'config.json').read_text(encoding='utf-8-sig'))
    existing=set(config['cold_files']);selected=[]
    for root in Path('C:/').iterdir():
        if not root.is_dir() or root.is_symlink() or not root.name.startswith(PREFIXES):continue
        if str(root).casefold() in tasks or any(str(root).casefold() in ref for ref in references):continue
        for parent,dirs,files in os.walk(root):
            dirs[:]=[d for d in dirs if d.casefold() not in {'venv','.venv','deps','.git','__pycache__','node_modules','ticks','data'}]
            for name in files:
                p=Path(parent)/name
                if name not in NAMES or p.is_symlink() or str(p) in existing:continue
                stat=p.stat()
                if stat.st_size>=100000 and time.time()-stat.st_mtime>86400:selected.append((str(p),stat.st_size))
    config['cold_files']+= [p for p,_ in selected]
    temp=BASE/'config.extend.tmp'
    with temp.open('w',encoding='utf-8') as stream:
        json.dump(config,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,BASE/'config.json')
    print(json.dumps(dict(added_files=len(selected),added_bytes=sum(size for _,size in selected),paths=[p for p,_ in selected],evicted=False)),flush=True)
    # The existing service performs checksum verification and durable receipts before eviction.
    subprocess.run(['schtasks','/Run','/TN','KatarinaHFResearchArchiveSync'],capture_output=True,check=True)
if __name__=='__main__':main()
