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
import zlib

BASE = Path(os.environ.get('KATARINA_HF_BASE', r'C:\KatarinaDev\config\hf-storage' if os.name == 'nt'
                           else str(Path.home() / '.local/state/katarina/hf-storage')))
STATE = Path(os.environ.get('KATARINA_STATE_DIR', r'C:\KatarinaDev\state\owner-broker-readonly\readonly-observer'
                            if os.name == 'nt' else str(BASE.parent / 'runtime')))
REPO = os.environ.get('KATARINA_HF_REPO', 'alfaaulia/katarina-research-archive')
EXPECTED_ACCOUNT = os.environ.get('KATARINA_HF_ACCOUNT', 'alfaaulia')
RESERVE = 2 * 1024**3

def configure_runtime(config):
    global BASE, STATE, REPO, EXPECTED_ACCOUNT
    BASE = Path(config.get('base_dir', BASE)).expanduser().resolve()
    STATE = Path(config.get('state_dir', STATE)).expanduser().resolve()
    REPO = config.get('repo', REPO)
    EXPECTED_ACCOUNT = config.get('expected_account', EXPECTED_ACCOUNT)
    if not isinstance(REPO, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}/[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', REPO):
        raise RuntimeError('INVALID_REPOSITORY')
    if not isinstance(EXPECTED_ACCOUNT, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', EXPECTED_ACCOUNT):
        raise RuntimeError('INVALID_EXPECTED_ACCOUNT')
    if BASE == STATE:
        raise RuntimeError('STATE_AND_CREDENTIAL_DIRECTORIES_MUST_DIFFER')

def load_token(config):
    token = os.environ.get(config.get('token_env', 'HF_TOKEN'), '').strip()
    if not token:
        if os.name == 'nt':
            token = dpapi((BASE / 'token.dpapi').read_bytes(), decrypt=True).decode('ascii').strip()
        else:
            path = Path(os.environ.get('HF_TOKEN_FILE') or config.get('token_file') or BASE / 'token.secret')
            if path.is_symlink():
                raise RuntimeError('CREDENTIAL_SYMLINK_FORBIDDEN')
            stat = path.stat()
            if stat.st_mode & 0o077 or stat.st_uid != os.getuid():
                raise RuntimeError('CREDENTIAL_PERMISSIONS_REQUIRED')
            token = path.read_text(encoding='ascii').strip()
    if not re.fullmatch(r'hf_[A-Za-z0-9]{10,}', token):
        raise RuntimeError('INVALID_HF_CREDENTIAL')
    return token

def safe_remote_path(name, revision):
    if (not isinstance(name, str) or not isinstance(revision, str)
            or not re.fullmatch(r'[a-f0-9]{40}', revision)
            or not re.fullmatch(r'(?:objects/[a-f0-9]{2}/[a-f0-9]{64}\.gz|manifests/[a-f0-9]{64}/[a-f0-9]{64}\.json)', name)):
        raise RuntimeError('INVALID_PINNED_ARCHIVE_PATH')
    return 'https://huggingface.co/datasets/' + REPO + '/resolve/' + revision + '/' + name

def validate_cold_source(source):
    source = Path(source).resolve()
    if (source.is_relative_to(BASE.resolve()) or source.is_relative_to(STATE.resolve())
            or source.suffix.lower() not in ('.json', '.jsonl', '.csv', '.sqlite3')
            or any(word in source.name.lower() for word in ('private', 'credential', 'secret', 'token'))
            or source.suffix.lower() == '.sqlite3' and Path(str(source) + '-wal').exists()):
        raise RuntimeError('PROTECTED_SOURCE_EVICTION_FORBIDDEN')

def cooldown():
    path = BASE / 'cooldown.json'
    if path.exists():
        value = json.loads(path.read_text())
        if value.get('retry_epoch', 0) > time.time():
            return value
    return None

def publish_cooldown(results=(), errors=()):
    value = cooldown()
    if value:
        report = dict(status='WAITING_CLOUD_RATE_LIMIT', repo=REPO,
                      as_of_utc=utc(), next_retry_utc=datetime.fromtimestamp(value['retry_epoch'], timezone.utc).isoformat(),
                      results=list(results), errors=list(errors), free_after=shutil.disk_usage(STATE).free)
        atomic_json(STATE / 'hf-storage-status.json', report)
        print(json.dumps(report), flush=True)
        return True
    return False

def safe_error(error):
    if isinstance(error, sqlite3.Error):
        return getattr(error, 'sqlite_errorname', 'SQLITE_' + type(error).__name__)
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
        if self.api.whoami().get('name') != EXPECTED_ACCOUNT:
            raise RuntimeError('UNEXPECTED_ACCOUNT')
        try:
            info = self.api.repo_info(REPO, repo_type='dataset')
        except Exception as error:
            if getattr(getattr(error, 'response', None), 'status_code', None) != 404:
                raise
            self.api.create_repo(REPO, repo_type='dataset', private=True, exist_ok=True)
            info = self.api.repo_info(REPO, repo_type='dataset')
        if info.private is not True:
            raise RuntimeError('PRIVATE_REPOSITORY_REQUIRED')
    def upload(self, local, name):
        if cooldown():
            raise RuntimeError('CLOUD_RATE_LIMITED')
        try:
            info = self.api.upload_file(path_or_fileobj=str(local) if isinstance(local, (str, Path)) else local, path_in_repo=name,
                    repo_id=REPO, repo_type='dataset', commit_message='Preserve verified Katarina research archive')
        except Exception as error:
            response = getattr(error, 'response', None)
            if getattr(response, 'status_code', None) == 429:
                try:
                    delay = max(60, min(86400, int(response.headers.get('retry-after', '3600'))))
                except ValueError:
                    delay = 3600
                atomic_json(BASE / 'cooldown.json', dict(retry_epoch=time.time()+delay+60, reason='HTTP_429'))
                raise RuntimeError('CLOUD_RATE_LIMITED') from None
            raise
        return info.oid
    def download(self, name, revision, cache):
        import httpx
        cache = uncompressed_temporary(cache, directory=True)
        target = uncompressed_temporary(cache / 'payload.download')
        url = safe_remote_path(name, revision)
        # A short flat path avoids Windows MAX_PATH failures in nested Hub caches.
        with httpx.Client(follow_redirects=True, timeout=60) as client:
            with client.stream('GET', url, headers={'Authorization': 'Bearer ' + self.token}) as response:
                response.raise_for_status()
                with target.open('wb') as stream:
                    for block in response.iter_bytes(1024**2):
                        stream.write(block)
        return target
    def download_memory(self, name, revision, limit=32*1024**2):
        import httpx
        url = safe_remote_path(name, revision)
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
    def verify_stream(self, name, revision, manifest):
        import httpx
        url = safe_remote_path(name, revision)
        with httpx.Client(follow_redirects=True, timeout=60) as client:
            with client.stream('GET', url, headers={'Authorization': 'Bearer ' + self.token}) as response:
                response.raise_for_status()
                verify_chunks(response.iter_bytes(65536), manifest)
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
def verify_chunks(chunks, manifest):
    """Verify a remote gzip stream without staging another archive copy on disk."""
    packed_hash, source_hash = hashlib.sha256(), hashlib.sha256()
    packed_size = source_size = 0
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    for chunk in chunks:
        packed_hash.update(chunk)
        packed_size += len(chunk)
        if packed_size > manifest['archive_bytes']:
            raise RuntimeError('ARCHIVE_SIZE_EXCEEDED')
        pending = chunk
        while pending:
            block = decoder.decompress(pending, 1024**2)
            source_size += len(block)
            source_hash.update(block)
            if source_size > manifest['source_bytes']:
                raise RuntimeError('RESTORE_SIZE_EXCEEDED')
            pending = decoder.unconsumed_tail
    if not decoder.eof or decoder.unused_data:
        raise RuntimeError('ARCHIVE_STREAM_INCOMPLETE')
    if packed_size != manifest['archive_bytes'] or packed_hash.hexdigest() != manifest['archive_sha256']:
        raise RuntimeError('ARCHIVE_CHECKSUM_MISMATCH')
    if source_size != manifest['source_bytes'] or source_hash.hexdigest() != manifest['source_sha256']:
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

def archive_file(source, hub, ledger, work, *, evict=False, allowed_cold=(), logical_source=None):
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
    if evict:
        validate_cold_source(source)
    if logical_source is not None and (evict or not re.fullmatch(r'state/[A-Za-z0-9_./-]+', logical_source)
                                       or '..' in logical_source.split('/')):
        raise RuntimeError('INVALID_LOGICAL_SOURCE')
    identity = 'logical:' + logical_source if logical_source is not None else str(source).casefold()
    key = hashlib.sha256(identity.encode()).hexdigest()
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
        same = (old.get('source_bytes') == before.st_size and old.get('source_mtime_ns') == before.st_mtime_ns)
        if logical_source is not None:
            same = old.get('source_sha256') == sha_file(source)
        if same and old.get('repo') == REPO:
            return dict(status='UNCHANGED', source=str(source), source_bytes=before.st_size,
                        sha256=old['source_sha256'],restore_verified=bool(old.get('restore_verified_utc')))
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
        if logical_source is not None:
            manifest['logical_source'] = logical_source
        if hasattr(hub, 'verify_stream'):
            hub.verify_stream(remote, revision, manifest)
        else:
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
        if hasattr(hub, 'download_memory'):
            manifest_bytes = hub.download_memory(remote_manifest, manifest_revision)
        else:
            manifest_bytes = hub.download(remote_manifest, manifest_revision, temp / 'manifest-download').read_bytes()
        if manifest_bytes != local_manifest.read_bytes():
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
    safe_remote_path(manifest.get('object'), manifest.get('object_revision'))
    for key in ('source_bytes', 'archive_bytes'):
        if type(manifest.get(key)) is not int or manifest[key] < 0:
            raise RuntimeError('INVALID_RESTORE_SIZE')
    for key in ('source_sha256', 'archive_sha256'):
        if not isinstance(manifest.get(key), str) or not re.fullmatch(r'[a-f0-9]{64}', manifest[key]):
            raise RuntimeError('INVALID_RESTORE_CHECKSUM')
    destination = Path(destination)
    if destination.exists():
        if sha_file(destination) == manifest['source_sha256']:
            return destination
        raise RuntimeError('RESTORE_DESTINATION_EXISTS')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < RESERVE + manifest['source_bytes'] + manifest['archive_bytes']:
        raise RuntimeError('RESTORE_WAITING_DISK_RESERVE')
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
    deadline = time.monotonic() + 1800
    def interrupted():
        return int(time.monotonic() > deadline or
                   shutil.disk_usage(target.parent).free < RESERVE + 32 * 1024**2)
    if os.name == 'nt':
        # Avoid NTFS recompressing SQLite's changing pages on every write when
        # a plain copy fits. Compress the completed snapshot once instead.
        plain = shutil.disk_usage(target.parent).free > RESERVE + source.stat().st_size + 64 * 1024**2
        subprocess.run(['compact.exe', '/U' if plain else '/C', '/I', '/Q', str(target.parent)],
                       capture_output=True, check=True, timeout=10)
    # VACUUM INTO creates a consistent, compact copy without changing the live database.
    with contextlib.closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=5)) as src:
        src.set_progress_handler(interrupted, 10000)
        src.execute('PRAGMA cache_size=-4096')
        src.execute('PRAGMA temp_store=MEMORY')
        src.execute('VACUUM INTO ?', (str(target),))
    with contextlib.closing(sqlite3.connect(target.as_uri() + '?mode=ro', uri=True, timeout=5)) as dst:
        dst.set_progress_handler(interrupted, 10000)
        if dst.execute('pragma quick_check').fetchone()[0] != 'ok':
            raise RuntimeError('BACKUP_INTEGRITY_FAILED')
    if os.name == 'nt':
        subprocess.run(['compact.exe', '/C', '/I', '/Q', str(target)],
                       capture_output=True, check=True, timeout=120)

@contextlib.contextmanager
def capture_json_file(source, work):
    """Capture one complete atomic JSON version before slow network operations."""
    source, work = Path(source), Path(work)
    for attempt in range(3):
        try:
            raw = source.read_bytes()
            if len(raw) > 2 * 1024**2:
                raise RuntimeError('JSON_CAPTURE_LIMIT')
            json.loads(raw)
            break
        except FileNotFoundError:
            if attempt == 2:
                raise
            time.sleep(.1)
    with tempfile.TemporaryDirectory(prefix='capture-', dir=work) as directory:
        snapshot = Path(directory) / source.name
        snapshot.write_bytes(raw)
        yield snapshot

def sync(config, hub):
    work = BASE / 'work'
    ledger = BASE / 'manifests'
    work.mkdir(parents=True, exist_ok=True)
    status_path = STATE / 'hf-storage-status.json'
    free_before = shutil.disk_usage(STATE).free
    results, errors = [], []
    if publish_cooldown():
        return
    # Configured archive budget; this threshold does not infer provider billing.
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
            if publish_cooldown(results, errors):
                return
    for name in config.get('sync_files', []):
        source = Path(name)
        if not source.is_file():
            continue
        try:
            with capture_json_file(source, work) as snapshot:
                result = archive_file(snapshot, hub, ledger, work,
                                      logical_source='state/' + source.resolve().relative_to(STATE.resolve()).as_posix())
                result['snapshot_source'] = str(source)
                results.append(result)
        except Exception as e:
            record = dict(source=str(source), error=safe_error(e))
            errors.append(record)
            print(json.dumps(dict(status='RETRY_PENDING', **record)), flush=True)
            if publish_cooldown(results, errors):
                return
    last_backup = BASE / 'backup-clock.json'
    clock = json.loads(last_backup.read_text()) if last_backup.exists() else {}
    completed = clock.setdefault('databases', {})
    # Adopt already verified backups from older all-or-nothing clock versions.
    if status_path.exists():
        previous = json.loads(status_path.read_text())
        for result in previous.get('results', []):
            name = result.get('database_source')
            if name and result.get('restore_verified'):
                completed.setdefault(name, dict(last_success_epoch=datetime.fromisoformat(previous['as_of_utc']).timestamp()))
    if config.get('backup_databases'):
        backups_ok = True
        for name in config.get('backup_databases', []):
            source = Path(name)
            if not source.is_file():
                backups_ok = False
                errors.append(dict(source=str(source),error='BACKUP_SOURCE_MISSING'))
                continue
            if time.time() - completed.get(name, {}).get('last_success_epoch', clock.get('last_success_epoch', 0)) < 86400:
                results.append(dict(status='BACKUP_CURRENT', database_source=name))
                continue
            try:
                with tempfile.TemporaryDirectory(prefix='snapshot-', dir=work) as d:
                    snapshot = Path(d) / source.name
                    backup_database(source, snapshot)
                    result = archive_file(snapshot, hub, ledger, work,
                                          logical_source='state/' + source.resolve().relative_to(STATE.resolve()).as_posix())
                    result['database_source'] = str(source)
                    results.append(result)
                    completed[name] = dict(last_success_epoch=time.time(), sha256=result['sha256'])
                    atomic_json(last_backup, clock)
                    print(json.dumps(result), flush=True)
            except Exception as e:
                backups_ok = False
                record = dict(source=str(source), error=safe_error(e))
                errors.append(record)
                print(json.dumps(dict(status='RETRY_PENDING', **record)), flush=True)
                if publish_cooldown(results, errors):
                    return
        if backups_ok:
            clock.update(last_success_epoch=time.time(), as_of_utc=utc())
        atomic_json(last_backup, clock)
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
    config = json.loads(Path(a.config).read_text(encoding='utf-8-sig'))
    configure_runtime(config)
    import sys
    client_dir = config.get('client_dir') or os.environ.get('KATARINA_HF_CLIENT_DIR')
    if client_dir or os.name == 'nt':
        sys.path.insert(0, client_dir or r'C:\KatarinaDev\runtime\hf-client')
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    from filelock import FileLock
    with FileLock(str(BASE / 'sync.lock'), timeout=1):
        if not a.restore_manifest and publish_cooldown():
            return
        hub = Hub(load_token(config))
        if a.restore_manifest:
            if not a.destination:
                raise RuntimeError('RESTORE_DESTINATION_REQUIRED')
            restore_file(json.loads(Path(a.restore_manifest).read_text()), hub, a.destination)
            print('RESTORE_VERIFIED')
        else:
            # Only this locked service owns these temporary directories. Recover
            # staging space left behind by an interrupted scheduled task.
            for stale in (BASE / 'work').glob('*'):
                if stale.is_dir() and not stale.is_symlink() and stale.name.startswith(('snapshot-', 'capture-', 'archive-')):
                    shutil.rmtree(stale)
            sync(config, hub)
if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # SDK exceptions may contain request bodies: do not print them.
        print(json.dumps(dict(status='FAILED', error=type(error).__name__)), flush=True)
        raise SystemExit(1) from None
