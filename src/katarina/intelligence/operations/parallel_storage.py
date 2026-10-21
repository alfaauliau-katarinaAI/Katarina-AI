"""Enable WAL before workers start; never delete or rebuild evidence databases."""
from contextlib import closing
from pathlib import Path
import sqlite3


def prepare_parallel_storage(root):
    root=Path(root)
    names=['context.sqlite3','experiment-jobs.sqlite3','network-doctor.sqlite3',
           'demo-forward/experiment.sqlite3','demo-forward/orders.sqlite3']
    modes={}
    for name in names:
        path=root/name
        if not path.parent.is_dir():continue
        with closing(sqlite3.connect(path,timeout=5)) as db:
            mode=db.execute('PRAGMA journal_mode=WAL').fetchone()[0]
            if mode!='wal':raise RuntimeError('PARALLEL_STORAGE_UNAVAILABLE')
            modes[name]=mode
    return modes
