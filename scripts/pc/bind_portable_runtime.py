"""Bind an existing embedded Python to its approved checkout; no installer/network."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


def bind_runtime(runtime_root, source_root):
    runtime, source = Path(runtime_root).resolve(), Path(source_root).resolve()
    target = runtime/'python312._pth'
    embedded = target.is_file()
    if not embedded:
        site = runtime/'Lib/site-packages'
        if not site.is_dir():
            raise ValueError('portable_runtime_and_source_required')
        target = site/'katarina-canonical.pth'
    if (not (source/'src/katarina/intelligence/cognition/unified_brain.py').is_file()
            or any(c in str(source) for c in '\r\n')):
        raise ValueError('portable_runtime_and_source_required')
    original = target.read_bytes() if target.exists() else b''
    if len(original) > 65536:
        raise ValueError('portable_path_file_too_large')
    old = original.decode('utf-8-sig').splitlines()
    canonical = [str(source/'src'), str(source)]
    # Canonical code precedes old workspace packages; keep stdlib/site packages
    # and unrelated existing paths rather than deleting another runtime's files.
    lines = canonical + [line for line in old if line.strip() not in canonical]
    updated = ('\n'.join(lines)+'\n').encode('utf-8')
    before = sha256(original).hexdigest()
    if updated != original:
        backup = target.with_name(target.name+'.before-binding-'+before+'.bak')
        if backup.exists() and backup.read_bytes() != original:
            raise ValueError('portable_path_backup_conflict')
        if not backup.exists():
            backup.write_bytes(original)
        temp = target.with_name(target.name+'.binding.tmp')
        temp.write_bytes(updated)
        temp.replace(target)
    return dict(runtime_kind='EMBEDDED' if embedded else 'FULL', changed=updated != original, before_sha256=before,
                after_sha256=sha256(updated).hexdigest(), canonical_source_bound=True,
                import_probe_verified=False, orders_submitted=0,live_execution_authorized=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime-root',required=True)
    parser.add_argument('--source-root',required=True)
    args=parser.parse_args()
    print(json.dumps(bind_runtime(args.runtime_root,args.source_root),sort_keys=True))


if __name__=='__main__':
    main()
