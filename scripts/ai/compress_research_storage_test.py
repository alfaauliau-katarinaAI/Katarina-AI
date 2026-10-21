"""Reversible NTFS compression of research storage, with byte identity verification."""
from pathlib import Path
from contextlib import closing
import hashlib,json,shutil,sqlite3,subprocess
ROOT=Path(r'C:\KatarinaDev\state\owner-broker-readonly\readonly-observer')
TARGET=ROOT/'experiment-jobs.sqlite3'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()
s=read(ROOT/'continuous-status.json');e=read(ROOT/'demo-forward/executor.json')
assert s.get('production_execution') is False and s.get('live_execution_authorized') is False and s.get('orders_submitted')==0
assert e.get('independent') is True and e.get('mode')=='DEMO' and e.get('live_authorized') is False
assert TARGET.is_file() and TARGET.stat().st_size<600*1024**2
free=shutil.disk_usage(ROOT).free
subprocess.run(['schtasks','/End','/TN','KatarinaOwnerContinuousReadonly'],capture_output=True,check=True)
subprocess.run(['schtasks','/End','/TN','KatarinaTechnicalMonitorPublisher'],capture_output=True)
try:
    with closing(sqlite3.connect(TARGET.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        before_counts={name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ('trials','stress_reviews','research_reports','gemini_hypotheses')}
    before=digest(TARGET)
    result=subprocess.run(['compact.exe','/C','/I','/Q',str(TARGET)],capture_output=True,timeout=60)
    after=digest(TARGET)
    assert before==after,'RESEARCH_FILE_BYTES_CHANGED'
    with closing(sqlite3.connect(TARGET.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        after_counts={name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in before_counts}
    assert after_counts==before_counts,'RESEARCH_COUNTS_CHANGED'
    print(json.dumps(dict(compression_returncode=result.returncode,bytes_identical=True,counts_identical=True,quick_check='ok',free_before=free,free_after=shutil.disk_usage(ROOT).free,records=after_counts)),flush=True)
finally:
    subprocess.run(['schtasks','/Run','/TN','KatarinaOwnerContinuousReadonly'],capture_output=True,check=True)
    subprocess.run(['schtasks','/Run','/TN','KatarinaTechnicalMonitorPublisher'],capture_output=True,check=True)
assert read(ROOT/'demo-forward/executor.json')['pid']==e['pid'],'executor_changed'
print(json.dumps(dict(restarted_scanner=True,untouched_executor_pid=e['pid'])),flush=True)
