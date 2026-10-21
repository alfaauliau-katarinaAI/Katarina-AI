"""One guarded bounded report-batch check; always restore the observer task."""
from pathlib import Path
import json,time,subprocess
from katarina.intelligence.lab.research_reports import publish_reports
root=Path(r'C:\KatarinaDev\state\owner-broker-readonly\readonly-observer')
d=json.loads((root/'demo-forward/status.json').read_text())
assert d['broker_positions_open']==0 and d['unresolved_submissions']==0
subprocess.run(['schtasks','/End','/TN','KatarinaOwnerContinuousReadonly'],check=True)
try:
    t=time.monotonic()
    count=publish_reports(root,batch=16)
    p=json.loads((root/'research-reports.json').read_text())
    print('NEW_REPORTS',count,'SECONDS',round(time.monotonic()-t,3),flush=True)
    print(json.dumps({k:p.get(k) for k in ['as_of_utc','reviewed_experiments','unreported_experiments']}),flush=True)
finally:
    subprocess.run(['schtasks','/Run','/TN','KatarinaOwnerContinuousReadonly'],check=True)
