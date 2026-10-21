"""Trusted local Owner research console; same brain, memory and host lock.

No network, scheduler, model endpoint, position change or live activation. JSON
input must be a private file, never a public repository with account data.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from katarina.host import state_directory
from katarina.intelligence.cognition.observer import lock_worker
from katarina.intelligence.news.public_context import ContextStore
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.memory.store import MemoryStore


@contextmanager
def research_runtime(root):
    lock = lock_worker(root)
    context = memory = None
    try:
        context = ContextStore(root / 'context.sqlite3')
        memory = MemoryStore(root / 'cognitive-memory.sqlite3')
        brain = UnifiedKatarinaBrain(context.db, memory)
        yield brain.control.research_review
    finally:
        try:
            if memory is not None:
                memory.close()
        finally:
            try:
                if context is not None:
                    context.db.close()
            finally:
                lock.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local Owner research review — LIVE OFF')
    parser.add_argument('action', choices=('register', 'trial', 'review', 'weekly'))
    parser.add_argument('--state-dir')
    parser.add_argument('--input', help='Private JSON input; omit for weekly report')
    args = parser.parse_args(argv)
    if (args.action == 'weekly') != (args.input is None):
        parser.error('register/trial/review require --input; weekly takes no input')
    payload = json.loads(Path(args.input).read_text(encoding='utf-8')) if args.input else {}
    if not isinstance(payload, dict) or 'now' in payload:
        parser.error('input must be a JSON object without a caller-supplied clock')
    now = datetime.now(timezone.utc)
    with research_runtime(state_directory(args.state_dir)) as review:
        if args.action == 'weekly':
            result = review.weekly_report(as_of=now)
        else:
            operation = {'register': review.register, 'trial': review.record_trial,
                         'review': review.owner_review}[args.action]
            result = operation(**payload, now=now)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError, RuntimeError):
        print('OWNER_RESEARCH_BLOCKED: periksa input dan integritas state. LIVE OFF.', file=sys.stderr)
        raise SystemExit(2)
