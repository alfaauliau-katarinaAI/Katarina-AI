"""Private research archive with verified restore, local cache, and explicit cold-file eviction."""
import argparse
import contextlib
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time

BASE = Path(r'C:\KatarinaDev\config\hf-storage')
STATE = Path(r'C:\KatarinaDev\state\owner-broker-readonly\readonly-observer')
REPO = 'alfaaulia/katarina-research-archive'
RESERVE = 2 * 1024**3
def safe_error(error):
    text = str(error)
    return text if re.fullmatch(r'[A-Z][A-Z0-9_]{2,79}', text) else type(error).__name__

def utc():
    return datetime.now(timezone.utc).isoformat()
def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024**2), b''):
            h.update(b)
    return h.hexdigest()
def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, sort_keys=True)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
def dpapi(data, decrypt=False):
    import ctypes
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]
    buf = ctypes.create_string_buffer(data)
    src = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    out = Blob()
    if decrypt:
        ok = ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(src), None, None, None, None, 1, ctypes.byref(out))
    else:
        ok = ctypes.windll.crypt32.CryptProtectData(ctypes.byref(src), None, None, None, None, 5, ctypes.byref(out))
    if not ok:
        raise RuntimeError('DPAPI_FAILED')
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(ctypes.cast(out.pbData, ctypes.c_void_p))
class Hub:
    def __init__(self, token):
        from huggingface_hub import HfApi
        self.token = token
        self.api = HfApi(token=token)
        if self.api.whoami().get('name') != 'alfaaulia':
            raise RuntimeError('UNEXPECTED_ACCOUNT')
        self.api.create_repo(REPO, repo_type='dataset', private=True, exist_ok=True)
        if self.api.repo_info(REPO, repo_type='dataset').private is not True:
            raise RuntimeError('PRIVATE_REPOSITORY_REQUIRED')
    def upload(self, local, name):
        info = self.api.upload_file(path_or_fileobj=str(local) if isinstance(local, (str, Path)) else local, path_in_repo=name,
                repo_id=REPO, repo_type='dataset', commit_message='Preserve verified Katarina research archive')
        return info.oid
    def download(self, name, revision, cache):
        from huggingface_hub import hf_hub_download
        return Path(hf_hub_download(REPO, name, repo_type='dataset', revision=revision,
                    token=self.token, cache_dir=str(cache), force_download=True))
    def download_memory(self, name, revision, limit=32*1024**2):
        import httpx
        url = 'https://huggingface.co/datasets/' + REPO + '/resolve/' + revision + '/' + name
        parts, size = [], 0
        # httpx drops Authorization on cross-origin redirects to signed storage URLs.
        with httpx.Client(follow_redirects=True, timeout=60) as client:
            with client.stream('GET', url, headers={'Authorization': 'Bearer ' + self.token}) as response:
                response.raise_for_status()
                for block in response.iter_bytes(1024**2):
                    size += len(block)
                    if size > limit:
                        raise RuntimeError('MEMORY_ARCHIVE_LIMIT')
                    parts.append(block)
        return b''.join(parts)
    def stored_bytes(self):
        info = self.api.repo_info(REPO, repo_type='dataset', files_metadata=True)
        return sum(s.size or 0 for s in info.siblings)
def uncompressed_temporary(path, *, directory=False):
    """Avoid double-compressing gzip payloads on the compressed Windows staging volume."""
    path = Path(path)
    if directory:
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.touch()
    if os.name == 'nt':
        subprocess.run(['compact.exe', '/U', '/I', '/Q', str(path)],
                       capture_output=True, check=True, timeout=10)
    return path

def verify_archive(path, manifest):
    if sha_file(path) != manifest['archive_sha256']:
        raise RuntimeError('ARCHIVE_CHECKSUM_MISMATCH')
    h = hashlib.sha256()
    size = 0
    with gzip.open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024**2), b''):
            h.update(b)
            size += len(b)
            if size > manifest['source_bytes']:
                raise RuntimeError('RESTORE_SIZE_EXCEEDED')
    if h.hexdigest() != manifest['source_sha256'] or size != manifest['source_bytes']:
        raise RuntimeError('RESTORE_CHECKSUM_MISMATCH')
def verify_memory(data, manifest):
    if hashlib.sha256(data).hexdigest() != manifest['archive_sha256']:
        raise RuntimeError('ARCHIVE_CHECKSUM_MISMATCH')
    h, size = hashlib.sha256(), 0
    with gzip.GzipFile(fileobj=io.BytesIO(data), mode='rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
            size += len(block)
            if size > manifest['source_bytes']:
                raise RuntimeError('RESTORE_SIZE_EXCEEDED')
    if size != manifest['source_bytes'] or h.hexdigest() != manifest['source_sha256']:
        raise RuntimeError('RESTORE_CHECKSUM_MISMATCH')
def archive_memory(source, hub, receipt, before, key):
    """Bootstrap low disk migration without writing a temporary dataset to disk."""
    stream, digest = io.BytesIO(), hashlib.sha256()
    with source.open('rb') as src, gzip.GzipFile(filename='', fileobj=stream, mode='wb', compresslevel=3, mtime=0) as zipped:
        for block in iter(lambda: src.read(1024**2), b''):
            digest.update(block)
            zipped.write(block)
            if stream.tell() > 31*1024**2:
                raise RuntimeError('MEMORY_ARCHIVE_LIMIT')
    payload = stream.getvalue()
    if len(payload) > 32*1024**2:
        raise RuntimeError('MEMORY_ARCHIVE_LIMIT')
    if source.stat().st_mtime_ns != before.st_mtime_ns or source.stat().st_size != before.st_size:
        raise RuntimeError('SOURCE_CHANGED')
    packed_hash = hashlib.sha256(payload).hexdigest()
    remote = 'objects/' + packed_hash[:2] + '/' + packed_hash + '.gz'
    revision = hub.upload(io.BytesIO(payload), remote)
    manifest = dict(schema_version=1, repo=REPO, source=str(source), source_bytes=before.st_size,
                    source_mtime_ns=before.st_mtime_ns, source_sha256=digest.hexdigest(),
                    archive_bytes=len(payload), archive_sha256=packed_hash, object=remote,
                    object_revision=revision, archived_utc=utc(), restore_verified_utc=utc())
    verify_memory(hub.download_memory(remote, revision), manifest)
    if sha_file(source) != manifest['source_sha256'] or source.stat().st_mtime_ns != before.st_mtime_ns:
        raise RuntimeError('SOURCE_CHANGED_AFTER_UPLOAD')
    remote_manifest = 'manifests/' + key + '/' + manifest['source_sha256'] + '.json'
    encoded = (json.dumps(manifest, sort_keys=True) + '\n').encode()
    manifest_revision = hub.upload(io.BytesIO(encoded), remote_manifest)
    if hub.download_memory(remote_manifest, manifest_revision) != encoded:
        raise RuntimeError('MANIFEST_CHECKSUM_MISMATCH')
    manifest.update(manifest_object=remote_manifest, manifest_revision=manifest_revision, evicted=False)
    atomic_json(receipt, manifest)
    marker = source.with_name(source.name + '.hf-cloud.json')
    atomic_json(marker, manifest)
    if source.stat().st_mtime_ns != before.st_mtime_ns or sha_file(source) != manifest['source_sha256']:
        raise RuntimeError('SOURCE_CHANGED_BEFORE_EVICTION')
    source.unlink()
    manifest['evicted'] = True
    atomic_json(receipt, manifest)
    atomic_json(marker, manifest)
    return dict(status='ARCHIVED', source=str(source), source_bytes=before.st_size,
                archive_bytes=len(payload), sha256=manifest['source_sha256'], evicted=True,
                restore_verified=True, memory_bootstrap=True)

def archive_file(source, hub, ledger, work, *, evict=False, allowed_cold=()):
    source = Path(source)
    if source.is_symlink():
        raise RuntimeError('SYMLINK_SOURCE_FORBIDDEN')
    source = source.resolve()
    if not source.is_file():
        raise RuntimeError('INVALID_SOURCE')
    before = source.stat()
    cold = source in {Path(p).resolve() for p in allowed_cold}
    if evict and (not cold or time.time() - before.st_mtime < 86400):
        raise RuntimeError('EVICTION_NOT_ALLOWLISTED_OR_NOT_COLD')
    key = hashlib.sha256(str(source).casefold().encode()).hexdigest()
    work, ledger = Path(work), Path(ledger)
    work.mkdir(parents=True, exist_ok=True)
    ledger.mkdir(parents=True, exist_ok=True)
    receipt = ledger / (key + '.json')
    if evict and receipt.exists() and json.loads(receipt.read_text()).get('evicted') is True:
        return dict(status='RESTORED_CACHE_PROTECTED', source=str(source), source_bytes=before.st_size)
    if evict:
        return archive_memory(source, hub, receipt, before, key)
    if not evict and receipt.exists():
        old = json.loads(receipt.read_text())
        if old.get('source_bytes') == before.st_size and old.get('source_mtime_ns') == before.st_mtime_ns:
            return dict(status='UNCHANGED', source=str(source), source_bytes=before.st_size)
    with tempfile.TemporaryDirectory(prefix='archive-', dir=work) as temporary:
        temp = Path(temporary)
        packed = uncompressed_temporary(temp / 'payload.gz')
        h = hashlib.sha256()
        with source.open('rb') as src, packed.open('wb') as dst:
            with gzip.GzipFile(filename='', fileobj=dst, mode='wb', compresslevel=3, mtime=0) as out:
                for b in iter(lambda: src.read(1024**2), b''):
                    h.update(b)
                    out.write(b)
                    if shutil.disk_usage(work).free < RESERVE + 32 * 1024**2:
                        raise RuntimeError('ARCHIVE_WAITING_DISK_RESERVE')
        after = source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError('SOURCE_CHANGED')
        digest = h.hexdigest()
        archive_digest = sha_file(packed)
        remote = 'objects/' + archive_digest[:2] + '/' + archive_digest + '.gz'
        revision = hub.upload(packed, remote)
        manifest = dict(schema_version=1, repo=REPO, source=str(source), source_bytes=before.st_size,
                        source_mtime_ns=before.st_mtime_ns, source_sha256=digest,
                        archive_bytes=packed.stat().st_size, archive_sha256=archive_digest,
                        object=remote, object_revision=revision, archived_utc=utc())
        if shutil.disk_usage(work).free < RESERVE + packed.stat().st_size + 32 * 1024**2:
            raise RuntimeError('VERIFY_WAITING_DISK_RESERVE')
        uncompressed_temporary(temp / 'download', directory=True)
        downloaded = hub.download(remote, revision, temp / 'download')
        verify_archive(downloaded, manifest)
        if sha_file(source) != digest or source.stat().st_mtime_ns != before.st_mtime_ns:
            raise RuntimeError('SOURCE_CHANGED_AFTER_UPLOAD')
        manifest['restore_verified_utc'] = utc()
        remote_manifest = 'manifests/' + key + '/' + digest + '.json'
        local_manifest = temp / 'manifest.json'
        atomic_json(local_manifest, manifest)
        manifest_revision = hub.upload(local_manifest, remote_manifest)
        # Verify the manifest as well, before any local data is removed.
        manifest_copy = hub.download(remote_manifest, manifest_revision, temp / 'manifest-download')
        if manifest_copy.read_bytes() != local_manifest.read_bytes():
            raise RuntimeError('MANIFEST_CHECKSUM_MISMATCH')
        manifest['manifest_object'] = remote_manifest
        manifest['manifest_revision'] = manifest_revision
        manifest['evicted'] = False
        atomic_json(receipt, manifest)
        if evict:
            # Durable location marker precedes unlink. Only explicitly approved, inactive files.
            marker = source.with_name(source.name + '.hf-cloud.json')
            atomic_json(marker, manifest)
            if source.stat().st_mtime_ns != before.st_mtime_ns or sha_file(source) != digest:
                raise RuntimeError('SOURCE_CHANGED_BEFORE_EVICTION')
            source.unlink()
            manifest['evicted'] = True
            atomic_json(receipt, manifest)
            atomic_json(marker, manifest)
        return dict(status='ARCHIVED', source=str(source), source_bytes=before.st_size,
                    archive_bytes=manifest['archive_bytes'], evicted=evict,
                    sha256=digest, restore_verified=True)
def restore_file(manifest, hub, destination):
    if manifest.get('repo') != REPO:
        raise RuntimeError('WRONG_REPOSITORY')
    destination = Path(destination)
    if destination.exists():
        if sha_file(destination) == manifest['source_sha256']:
            return destination
        raise RuntimeError('RESTORE_DESTINATION_EXISTS')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='hf-restore-', dir=destination.parent) as tmp:
        tmp = Path(tmp)
        compressed = hub.download(manifest['object'], manifest['object_revision'], tmp / 'download')
        verify_archive(compressed, manifest)
        target = tmp / 'restored'
        with gzip.open(compressed, 'rb') as src, target.open('wb') as dst:
            shutil.copyfileobj(src, dst, 1024**2)
            dst.flush()
            os.fsync(dst.fileno())
        os.utime(target, ns=(manifest['source_mtime_ns'], manifest['source_mtime_ns']))
        # Refuse overwrite even if another worker restored it during the download.
        try:
            os.link(target, destination)
        except FileExistsError:
            if sha_file(destination) != manifest['source_sha256']:
                raise RuntimeError('RESTORE_RACE_CONFLICT')
    return destination
def backup_database(source, target):
    source, target = Path(source), Path(target)
    # Hold the normal reserve while creating a consistent SQLite backup.
    if shutil.disk_usage(source).free < RESERVE + 64 * 1024**2:
        raise RuntimeError('BACKUP_WAITING_DISK_RESERVE')
    deadline = time.monotonic() + 120
    def progress(*args):
        if time.monotonic() > deadline:
            raise RuntimeError('BACKUP_TIME_LIMIT')
        if shutil.disk_usage(target.parent).free < RESERVE + 32 * 1024**2:
            raise RuntimeError('BACKUP_WAITING_DISK_RESERVE')
    with contextlib.closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=5)) as src:
        with contextlib.closing(sqlite3.connect(target, timeout=5)) as dst:
            src.backup(dst, pages=1024, progress=progress, sleep=.1)
            if dst.execute('pragma quick_check').fetchone()[0] != 'ok':
                raise RuntimeError('BACKUP_INTEGRITY_FAILED')
def sync(config, hub):
    work = BASE / 'work'
    ledger = BASE / 'manifests'
    work.mkdir(parents=True, exist_ok=True)
    status_path = STATE / 'hf-storage-status.json'
    free_before = shutil.disk_usage(STATE).free
    results, errors = [], []
    # Leave 20 GB headroom within the currently documented private free allowance.
    used = hub.stored_bytes()
    if used > 80 * 1000**3:
        atomic_json(status_path, dict(status='PAUSED_CLOUD_QUOTA', cloud_bytes=used, as_of_utc=utc()))
        return
    for name in config.get('cold_files', []):
        source = Path(name)
        if not source.exists():
            continue
        try:
            results.append(archive_file(source, hub, ledger, work, evict=True,
                                        allowed_cold=config['cold_files']))
            print(json.dumps(results[-1]), flush=True)
        except Exception as e:
            record = dict(source=str(source), error=safe_error(e))
            errors.append(record)
            print(json.dumps(dict(status='RETRY_PENDING', **record)), flush=True)
    for name in config.get('sync_files', []):
        source = Path(name)
        if not source.is_file() or source.stat().st_size > 2 * 1024**2:
            continue
        try:
            results.append(archive_file(source, hub, ledger, work))
        except Exception as e:
            record = dict(source=str(source), error=safe_error(e))
            errors.append(record)
            print(json.dumps(dict(status='RETRY_PENDING', **record)), flush=True)
    last_backup = BASE / 'backup-clock.json'
    clock = json.loads(last_backup.read_text()) if last_backup.exists() else {}
    if time.time() - clock.get('last_success_epoch', 0) >= 86400:
        backups_ok = True
        for name in config.get('backup_databases', []):
            source = Path(name)
            if not source.is_file():
                continue
            try:
                with tempfile.TemporaryDirectory(prefix='snapshot-', dir=work) as d:
                    snapshot = Path(d) / source.name
                    backup_database(source, snapshot)
                    result = archive_file(snapshot, hub, ledger, work)
                    result['database_source'] = str(source)
                    results.append(result)
                    print(json.dumps(result), flush=True)
            except Exception as e:
                backups_ok = False
                record = dict(source=str(source), error=safe_error(e))
                errors.append(record)
                print(json.dumps(dict(status='RETRY_PENDING', **record)), flush=True)
        if backups_ok:
            atomic_json(last_backup, dict(last_success_epoch=time.time(), as_of_utc=utc()))
    report = dict(schema_version=1, status='SYNCED' if not errors else 'PARTIAL_RETRY_PENDING',
                  repo=REPO, as_of_utc=utc(), free_before=free_before,
                  free_after=shutil.disk_usage(STATE).free, results=results, errors=errors,
                  interval_minutes=10, live_authorized=False, pid=os.getpid())
    atomic_json(status_path, report)
    print(json.dumps(report), flush=True)
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=str(BASE / 'config.json'))
    p.add_argument('--restore-manifest')
    p.add_argument('--destination')
    a = p.parse_args()
    import sys
    sys.path.insert(0, r'C:\KatarinaDev\runtime\hf-client')
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    token = dpapi((BASE / 'token.dpapi').read_bytes(), decrypt=True).decode('ascii')
    hub = Hub(token)
    from filelock import FileLock
    with FileLock(str(BASE / 'sync.lock'), timeout=1):
        if a.restore_manifest:
            if not a.destination:
                raise RuntimeError('RESTORE_DESTINATION_REQUIRED')
            restore_file(json.loads(Path(a.restore_manifest).read_text()), hub, a.destination)
            print('RESTORE_VERIFIED')
        else:
            sync(json.loads(Path(a.config).read_text()), hub)
if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # SDK exceptions may contain request bodies: do not print them.
        print(json.dumps(dict(status='FAILED', error=type(error).__name__)), flush=True)
        raise SystemExit(1) from None
