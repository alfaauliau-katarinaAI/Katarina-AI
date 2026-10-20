"""Canonical scheduled entrypoint; configuration and credentials live outside code."""
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import argparse
import json
import os
import runpy
import sys

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    args=parser.parse_args()
    path=Path(args.config).expanduser().resolve()
    config=json.loads(path.read_text(encoding='utf-8-sig'))
    base=Path(config.get('base_dir',path.parent)).expanduser().resolve()
    if base != path.parent:
        raise RuntimeError('CONFIG_MUST_LIVE_IN_PRIVATE_BASE')
    log_path=base/'sync-v2.log'
    # Logs are operational only. Bound their disk footprint before starting.
    if log_path.exists() and log_path.stat().st_size>5*1024**2:
        os.replace(log_path,base/'sync-v2.previous.log')
    sys.argv=[str(Path(__file__).with_name('hf_archive_sync.py')),'--config',str(path)]
    with log_path.open('a',encoding='utf-8',buffering=1) as log:
        with redirect_stdout(log),redirect_stderr(log):
            runpy.run_path(sys.argv[0],run_name='__main__')

if __name__=='__main__':main()
