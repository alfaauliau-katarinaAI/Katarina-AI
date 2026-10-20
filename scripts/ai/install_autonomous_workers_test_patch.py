"""Guarded installation on the ahead-of-main Windows test runtime."""
import hashlib
import json
from pathlib import Path
import shutil


def install(root,payload_path):
    root=Path(root);payload=json.loads(Path(payload_path).read_text(encoding='utf-8'))
    pool=root/'src/katarina/intelligence/autonomous_research.py'
    current=pool.read_text(encoding='utf-8')
    replacement=payload['src/katarina/intelligence/autonomous_research.py']
    if 'research_capacity(self.root)' not in replacement or 'pid=os.getpid()' not in replacement:
        raise RuntimeError('INCOMPLETE_RESEARCH_POOL_PAYLOAD')
    expected={'b95821f06fc8c771f7067af7a95608a1490023b5c4c1ce9ae94caf5806d95984',
              'c8337e02c45405875272add1c6da295e4a19611e1f37c8a6894deeed7ce5f3ae',
              hashlib.sha256(replacement.encode()).hexdigest()}
    if hashlib.sha256(current.encode()).hexdigest() not in expected:
        raise RuntimeError('UNKNOWN_RESEARCH_POOL_SOURCE')
    sources={root/name:value for name,value in payload.items()}
    observer=root/'src/katarina/intelligence/continuous_observation.py'
    s=observer.read_text(encoding='utf-8');old="if getattr(config,'demo_experiments',False):"
    new="if getattr(config,'demo_experiments',False) and not (root/'demo-forward'/'independent.enabled').exists():"
    if new not in s:
        if s.count(old)!=1:raise RuntimeError('UNKNOWN_OBSERVER_DEMO_HOOK')
        s=s.replace(old,new)
    sources[observer]=s
    public=root/'src/katarina/monitoring/public_runtime.py';s=public.read_text(encoding='utf-8')
    if "public_board['worker_runtime']" not in s:
        marker="    public_board['public_scope']='RESEARCH_GRAPH_AND_ENTRY_ONLY'"
        if s.count(marker)!=1:raise RuntimeError('UNKNOWN_PUBLIC_RUNTIME_HOOK')
        s=s.replace(marker,"    from katarina.monitoring.worker_runtime import read_worker_runtime\n    public_board['worker_runtime']=read_worker_runtime(root,pid)\n"+marker)
    sources[public]=s
    demo=root/'src/katarina/intelligence/demo_forward.py';s=demo.read_text(encoding='utf-8')
    if 'from katarina.monitoring.snapshot_io import replace_snapshot' not in s:
        if 'from __future__ import annotations' in s:s=s.replace('from __future__ import annotations','from __future__ import annotations\nfrom katarina.monitoring.snapshot_io import replace_snapshot')
        else:s+='\nfrom katarina.monitoring.snapshot_io import replace_snapshot\n'
    s=s.replace("tmp.replace(self.private/'status.json')","replace_snapshot(tmp,self.private/'status.json')")
    if "            self.permission='UNVERIFIED'\n            reason=self.boundary._identity_error()" not in s:
        s=s.replace("            reason=self.boundary._identity_error()","            self.permission='UNVERIFIED'\n            reason=self.boundary._identity_error()")
    sources[demo]=s
    for path,source in sources.items():compile(source,str(path),'exec')
    backup=root/'handoff-backups'/'autonomous-workers-20261020';backup.mkdir(parents=True,exist_ok=True)
    for path,source in sources.items():
        if path.exists():
            copy=backup/path.relative_to(root)
            copy.parent.mkdir(parents=True,exist_ok=True)
            if not copy.exists():shutil.copy2(path,copy)
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source,encoding='utf-8')
    print(json.dumps({'installed':True,'files':len(sources),'live_authorized':False}))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--payload',required=True);a=p.parse_args();install(a.root,a.payload)
