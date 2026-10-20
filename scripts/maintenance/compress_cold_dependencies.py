"""Lossless NTFS compression of explicit cold dependency folders, never research data.

No deletion or relocation. Records SHA-256 of every file before and after; refuses
non-dependency paths, recent writes and symlinks; selects only DLL/PYD binaries.
Run on Windows with --root for each dated experiment's deps directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def compress(roots, report):
    if os.name!='nt':raise RuntimeError('Windows NTFS required')
    inventory={}
    for root in roots:
        root=Path(root).resolve()
        if not root.is_dir():raise ValueError('Dependency directory missing')
        if not ((root.name=='deps' and re.fullmatch(r'[A-Za-z]+2026101[67]',root.parent.name)) or (root.parts[-3:]==('venv','Lib','site-packages') and re.fullmatch(r'[A-Za-z]+2026101[67]',root.parents[2].name))):
            raise ValueError('Only explicit dated test dependency folders allowed')
        files=[]
        for base,dirs,names in os.walk(root,followlinks=False):
            if any((Path(base)/d).is_symlink() for d in dirs):raise ValueError('Symlink directory')
            for name in names:
                p=Path(base)/name
                if p.is_symlink():raise ValueError('Symlink file')
                if p.suffix.lower() not in {'.dll','.pyd'}:continue
                if p.stat().st_mtime>time.time()-86400:raise ValueError('Recent dependency write')
                files.append(p)
        inventory[str(root)]={str(p):digest(p) for p in files}
    proof={'before_free':shutil.disk_usage('C:/').free,'roots':inventory,'verified':False}
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(proof),encoding='utf-8')
    print(json.dumps({'prepared_roots':len(inventory),'files':sum(map(len,inventory.values())),'before_free':proof['before_free']}),flush=True)
    for root,files in inventory.items():
        proc=subprocess.run(['compact.exe','/C','/I','/Q','/S','*.dll','*.pyd'],cwd=root,capture_output=True,text=True)
        if proc.returncode:raise RuntimeError('NTFS compression failed: '+str(proc.returncode))
        for path,sha in files.items():
            if digest(Path(path))!=sha:raise RuntimeError('Dependency content changed: '+path)
        print(json.dumps({'root':root,'sha256_verified':len(files),'free':shutil.disk_usage('C:/').free}),flush=True)
    proof.update(verified=True,after_free=shutil.disk_usage('C:/').free)
    report.write_text(json.dumps(proof),encoding='utf-8')
    print(json.dumps({'verified':True,'before_free':proof['before_free'],'after_free':proof['after_free']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',action='append',required=True);p.add_argument('--report',required=True)
    a=p.parse_args();compress(a.root,a.report)
