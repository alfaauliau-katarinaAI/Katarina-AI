"""One bounded, guarded test-host index migration; always restore the observer task."""
from pathlib import Path
import json,sqlite3,time,subprocess
from katarina.intelligence.research_reports import prepare_report_indexes,publish_reports
root=Path(r'C:\KatarinaDev\state\owner-broker-readonly\readonly-observer')
d=json.loads((root/'demo-forward/status.json').read_text())
assert d['broker_positions_open']==0 and d['unresolved_submissions']==0
subprocess.run(['schtasks','/End','/TN','KatarinaOwnerContinuousReadonly'],check=True)
try:
    t=time.monotonic()
    with sqlite3.connect(root/'experiment-jobs.sqlite3',timeout=5) as db:
        deadline=time.monotonic()+45
        db.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
        prepare_report_indexes(db)
    print('INDEXES_READY_SECONDS',round(time.monotonic()-t,3),flush=True)
    count=publish_reports(root,batch=16)
    p=json.loads((root/'research-reports.json').read_text())
    print('NEW_REPORTS',count,'SECONDS',round(time.monotonic()-t,3),flush=True)
    print(json.dumps({k:p.get(k) for k in ['as_of_utc','reviewed_experiments','unreported_experiments']}),flush=True)
finally:
    subprocess.run(['schtasks','/Run','/TN','KatarinaOwnerContinuousReadonly'],check=True)
