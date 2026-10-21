"""Write budget for independent research; no data deletion or relocation."""
from pathlib import Path
import shutil

MIN_FREE = 2 * 1024**3
# Verified cold archive migration recovered more than this extra 256 MiB.
# The independent free-space guard still applies to every research write.
MAX_DATABASE = 768 * 1024**2
WRITE_RESERVE = 8 * 1024**2
# Writers share one SQLite file: wait for the single write lock instead of failing
# after 2 s. Stays below worker stop timeouts (15 s) so shutdown remains bounded.
DB_TIMEOUT = 10


def research_capacity(root, *, disk_usage=shutil.disk_usage):
    root=Path(root)
    free=disk_usage(root).free
    size=sum(p.stat().st_size for p in (root/'experiment-jobs.sqlite3',root/'experiment-jobs.sqlite3-wal') if p.exists())
    status=('PAUSED_LOW_DISK' if free<MIN_FREE+WRITE_RESERVE else
            'PAUSED_STORAGE_BUDGET' if size+WRITE_RESERVE>MAX_DATABASE else 'READY')
    return dict(status=status, database_bytes=size, database_limit_bytes=MAX_DATABASE,
                disk_free_bytes=free, disk_reserve_bytes=MIN_FREE)
