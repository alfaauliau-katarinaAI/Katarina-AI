"""Install inbox housekeeping on the existing test runtime without replacing it."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def install(source_root, payload):
    root=Path(source_root)
    module=root/'src/katarina/intelligence/file_housekeeping.py'
    doctor=root/'src/katarina/intelligence/network_doctor.py'
    original=doctor.read_text(encoding='utf-8')
    marker='        issues=[];repairs=self.repair_threads()'
    hook='''
        if self._budget('file_housekeeping',300):
            try:
                from katarina.intelligence.file_housekeeping import organize
                housekeeping=organize(self.root)
                self.state['housekeeping']=housekeeping
                self.trace.emit('MEMORY_WRITE','DONE',action='FILE_HOUSEKEEPING_CHECKED',count=housekeeping['moved'])
            except (OSError,ValueError):
                self.state['housekeeping']={'status':'RETRY_PENDING','scope':'HOUSEKEEPING_INBOX_ONLY'}
'''
    if 'FILE_HOUSEKEEPING_CHECKED' not in original:
        if original.count(marker)!=1:raise RuntimeError('UNKNOWN_DOCTOR_SOURCE')
        updated=original.replace(marker,marker+hook)
    else:updated=original
    if 'from katarina.monitoring.snapshot_io import replace_snapshot' not in updated:
        updated=updated.replace('from contextlib import closing','from katarina.monitoring.snapshot_io import replace_snapshot\nfrom contextlib import closing')
    updated=updated.replace("tmp.replace(self.root/'network-doctor.json')","replace_snapshot(tmp,self.root/'network-doctor.json')")
    compile(updated,str(doctor),'exec');compile(payload,str(module),'exec')
    backup=root/'handoff-backups'/'housekeeping-20261020'
    backup.mkdir(parents=True,exist_ok=True)
    saved=backup/'network_doctor.py'
    if not saved.exists():shutil.copy2(doctor,saved)
    module.write_text(payload,encoding='utf-8');doctor.write_text(updated,encoding='utf-8')
    print(json.dumps({'installed':True,'doctor_sha256':hashlib.sha256(updated.encode()).hexdigest(),'module_sha256':hashlib.sha256(payload.encode()).hexdigest()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--payload',required=True);a=p.parse_args()
    install(a.root,Path(a.payload).read_text(encoding='utf-8'))
