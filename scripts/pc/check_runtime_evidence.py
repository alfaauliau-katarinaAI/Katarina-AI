"""Print a redacted read-only readiness snapshot; no broker connection or writes."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from katarina.intelligence.operations.runtime_evidence import read_runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', required=True)
    parser.add_argument('--max-age-seconds', type=int, default=180)
    args = parser.parse_args()
    if not 30 <= args.max_age_seconds <= 3600:
        parser.error('freshness budget must be 30..3600 seconds')
    report = read_runtime(args.state_dir, max_age_seconds=args.max_age_seconds)
    print(json.dumps(report, sort_keys=True))
    return 0 if report['result'] == 'PASS_READONLY_SNAPSHOT_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
