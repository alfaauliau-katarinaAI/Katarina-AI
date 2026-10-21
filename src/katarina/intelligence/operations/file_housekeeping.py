"""Bounded, reversible organization of Katarina's own staging workspace.

Only files directly in housekeeping/inbox are movable. Runtime stores, broker
history, memory, configuration and executable files are never candidates.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from katarina.monitoring.snapshot_io import replace_snapshot

PROTECTED = ('tick', 'memory', 'memori', 'credential', 'secret', 'private',
             'config', 'sqlite', 'database', '.env', 'connection', 'model')
ALLOWED = {'.txt', '.md', '.json', '.jsonl', '.log', '.png', '.jpg', '.jpeg', '.pdf'}
MAX_BYTES = 4 * 1024 * 1024


def _plain(path):
    s = path.lstat()
    return not path.is_symlink() and not (getattr(s, 'st_file_attributes', 0) & 0x400)


def _digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def _record(workspace, entry):
    with (workspace / 'moves.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, sort_keys=True) + '\n')
        f.flush()
        os.fsync(f.fileno())


def organize(root, *, now=None, limit=16, min_age=300):
    """Move settled inbox files only; preserve content and journal every move."""
    now = time.time() if now is None else now
    root = Path(root).resolve(strict=True)
    workspace = root / 'housekeeping'
    inbox = workspace / 'inbox'
    # Reject junctions/symlinks before creating or traversing any child.
    for p in (workspace, inbox):
        if p.exists() and (not _plain(p) or not p.is_dir()):
            raise ValueError('HOUSEKEEPING_LINK_OR_NON_DIRECTORY')
        p.mkdir(exist_ok=True)
    for name in ('moves.jsonl', 'status.tmp', 'status.json'):
        control = workspace / name
        if control.exists() and (not _plain(control) or not control.is_file()):
            raise ValueError('HOUSEKEEPING_CONTROL_LINK')
    result = dict(status='CHECKED', pid=os.getpid(), checked=0, moved=0,
                  protected=0, deferred=0, errors=0,
                  scope='HOUSEKEEPING_INBOX_ONLY', deletes_allowed=False,
                  as_of_utc=datetime.fromtimestamp(now, timezone.utc).isoformat())
    # scandir is bounded even when a staging directory is unexpectedly large.
    started = time.monotonic()
    with os.scandir(inbox) as entries:
        for entry in entries:
            if result['checked'] >= min(64, max(1, limit)) or time.monotonic()-started > 2:
                break
            result['checked'] += 1
            source = inbox / entry.name
            try:
                name = source.name.lower()
                if (not _plain(source) or not entry.is_file(follow_symlinks=False)
                        or any(token in name for token in PROTECTED)
                        or source.suffix.lower() not in ALLOWED):
                    result['protected'] += 1
                    continue
                before = source.stat()
                if now-before.st_mtime < min_age or before.st_size > MAX_BYTES:
                    result['deferred'] += 1
                    continue
                category = ('reports' if 'report' in name or 'laporan' in name else
                            'logs' if source.suffix.lower() in {'.log', '.jsonl'} else
                            'documents' if source.suffix.lower() in {'.txt', '.md', '.pdf'} else
                            'images' if source.suffix.lower() in {'.png', '.jpg', '.jpeg'} else
                            'review')
                target_dir = workspace / category
                if target_dir.exists() and (not _plain(target_dir) or not target_dir.is_dir()):
                    raise ValueError('HOUSEKEEPING_TARGET_LINK')
                target_dir.mkdir(exist_ok=True)
                digest = _digest(source)
                after = source.stat()
                if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                    result['deferred'] += 1
                    continue
                ident = uuid.uuid4().hex
                target = target_dir / (source.stem[:100] + '--' + ident + source.suffix)
                record = dict(id=ident, source='inbox/'+source.name,
                              destination=category+'/'+target.name, sha256=digest,
                              bytes=before.st_size, reason='CLASSIFIED_STAGING_FILE',
                              at_utc=result['as_of_utc'])
                _record(workspace, dict(record, state='INTENT'))
                # Exclusive target reservation prevents overwrite. Failures leave
                # a recoverable INTENT, never an unrecorded destructive action.
                with target.open('xb'):
                    pass
                try:
                    os.replace(source, target)
                except OSError:
                    # Empty reservation is retained and auditable; no deletion.
                    _record(workspace, dict(record, state='DEFERRED'))
                    raise
                _record(workspace, dict(record, state='MOVED'))
                result['moved'] += 1
            except (OSError, ValueError):
                result['errors'] += 1
    result['status'] = 'REVIEW_REQUIRED' if result['errors'] else 'ORGANIZED' if result['moved'] else 'CHECKED'
    temp = workspace / 'status.tmp'
    temp.write_text(json.dumps(result) + '\n', encoding='utf-8')
    replace_snapshot(temp, workspace / 'status.json')
    return result


def restore(root, move_id):
    """Explicit, content-verified undo. Never overwrite the original location."""
    workspace = Path(root).resolve(strict=True) / 'housekeeping'
    if not _plain(workspace):
        raise ValueError('HOUSEKEEPING_LINK')
    records = [json.loads(line) for line in (workspace/'moves.jsonl').read_text(encoding='utf-8').splitlines()]
    moved = next((r for r in reversed(records) if r['id'] == move_id and r['state'] == 'MOVED'), None)
    if moved is None or any(r['id'] == move_id and r['state'] == 'RESTORED' for r in records):
        raise ValueError('MOVE_NOT_RESTORABLE')
    source, target = workspace / moved['destination'], workspace / moved['source']
    if (source.parent.parent != workspace or target.parent != workspace/'inbox'
            or not _plain(source.parent) or not _plain(target.parent)
            or not _plain(source) or target.exists() or _digest(source) != moved['sha256']):
        raise ValueError('RESTORE_CONFLICT_OR_CONTENT_CHANGED')
    with target.open('xb'):
        pass
    os.replace(source, target)
    _record(workspace, dict(moved, state='RESTORED', at_utc=datetime.now(timezone.utc).isoformat()))
    return target
