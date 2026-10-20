"""Hash the deployable code inventory; no runtime files or credentials are included."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CODE_DIRS=('src/katarina','scripts/ai','scripts/deployment','scripts/memory','mt5')
EXACT_FILES=('sites/runtime-monitor/worker/index.js','requirements-stage07.txt',
             'requirements-brain-observer.txt','requirements-pc.txt','requirements-hf-storage.txt',
             'config/hf-storage.example.json','ops/deployment/katarina-hf-storage.service',
             'ops/deployment/katarina-hf-storage.timer')

def inventory(root):
    root=Path(root);paths=set()
    for directory in CODE_DIRS:
        for path in (root/directory).rglob('*'):
            if path.is_file() and path.suffix in ('.py','.mq5','.mqh') and '__pycache__' not in path.parts:
                paths.add(path.relative_to(root).as_posix())
    paths.update(name for name in EXACT_FILES if (root/name).is_file())
    return sorted(paths)

def generate(root):
    root=Path(root);files={}
    for name in inventory(root):
        raw=(root/name).read_bytes()
        files[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                         normalized_sha256=hashlib.sha256(raw.removeprefix(b'\xef\xbb\xbf').replace(b'\r\n',b'\n')).hexdigest())
    return dict(schema_version=1,scope='CODE_AND_DEPENDENCY_LOCKS_ONLY',files=files,
                secrets_included=False,runtime_state_included=False,live_authorized=False)

def verify(root,manifest):
    root=Path(root);missing=[];changed=[];line_endings=[]
    for name,record in manifest['files'].items():
        if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('UNSAFE_MANIFEST_PATH')
        path=root/name
        if not path.is_file():missing.append(name);continue
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            changed.append(name);continue
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()==record['sha256']:continue
        if hashlib.sha256(raw.removeprefix(b'\xef\xbb\xbf').replace(b'\r\n',b'\n')).hexdigest()==record['normalized_sha256']:
            line_endings.append(name)
        else:changed.append(name)
    extra=sorted(set(inventory(root))-set(manifest['files']))
    return dict(status='MATCH' if not(missing or changed or extra) else 'DRIFT',
                checked=len(manifest['files']),missing=missing,changed=changed,extra=extra,
                line_endings_only=line_endings,live_authorized=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',default=str(ROOT))
    p.add_argument('--manifest',required=True);p.add_argument('--generate',action='store_true');p.add_argument('--output')
    a=p.parse_args();path=Path(a.manifest)
    if a.generate:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(generate(a.root),sort_keys=True,indent=2)+'\n',encoding='utf-8');return
    report=verify(a.root,json.loads(path.read_text(encoding='utf-8-sig')))
    if a.output:Path(a.output).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));raise SystemExit(0 if report['status']=='MATCH' else 1)

if __name__=='__main__':main()
