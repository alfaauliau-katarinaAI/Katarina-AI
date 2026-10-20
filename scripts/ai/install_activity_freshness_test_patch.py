"""Use current-process activity as freshness evidence during long research cycles."""
from pathlib import Path
import shutil
root=Path(r'C:\KatarinaGitTest-4e14b098')
p=root/'src/katarina/monitoring/public_runtime.py'
s=p.read_text(encoding='utf-8')
old='and -30<=heartbeat_age<=180)'
new="and (-30<=heartbeat_age<=180 or activity.get('fresh') is True))"
if new not in s:
    if s.count(old)!=1:raise RuntimeError('UNEXPECTED_TELEMETRY_SOURCE')
    s=s.replace(old,new)
    compile(s,str(p),'exec')
    saved=Path(r'C:\KatarinaDev\handoff-backups\snapshot-report-20261020\public_runtime.py')
    if not saved.exists():shutil.copy2(p,saved)
    p.write_text(s,encoding='utf-8')
print('ACTIVITY_FRESHNESS_FIX_INSTALLED')
