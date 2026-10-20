"""Task Scheduler entrypoint: native Python logging, unaffected by SDK stderr warnings."""
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import runpy
BASE=Path(r'C:\KatarinaDev\config\hf-storage')
SCRIPT=Path(r'C:\KatarinaGitTest-4e14b098\scripts\ai\hf_archive_sync.py')
if __name__=='__main__':
    with (BASE/'sync-v2.log').open('a',encoding='utf-8',buffering=1) as log:
        with redirect_stdout(log),redirect_stderr(log):
            runpy.run_path(str(SCRIPT),run_name='__main__')
