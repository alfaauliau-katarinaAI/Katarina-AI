"""Run the existing AI trainer on a reconciled MT5 research journal; no orders."""
from __future__ import annotations
import argparse
import json
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from katarina.intelligence.brain import KatarinaAIBrain
from katarina.research.mt5_journal import FEATURE_NAMES, load_journal
from katarina.research.independent_audit import audit


def evaluate(path: Path, expected_trades: int, expected_net_profit: Decimal) -> dict:
    data = load_journal(path, expected_trades=expected_trades, expected_net_profit=expected_net_profit)
    result = KatarinaAIBrain().train_candidate(data.rows, feature_names=FEATURE_NAMES)
    final_audit = audit(data)
    return {
        'schema_version': 1,
        'result': final_audit['result'],
        'journal_sha256': data.source_sha256,
        'rows': len(data.rows),
        'buy_rows': data.sides.count('BUY'), 'sell_rows': data.sides.count('SELL'),
        'journal_net_profit': str(sum(data.net_profits)),
        'aggregate_reconciled': True,
        'clock_basis': 'broker_wall_clock; entry_lower_bound; exit_upper_bound',
        'feature_schema': 'mt5_research_journal_v1',
        'validation': asdict(result),
        'independent_audit': final_audit,
        'data_provenance_verified': False,
        'research_only': True, 'strategy_validated': False,
        'live_execution_enabled': False,
        'limitations': ['report totals supplied by caller', 'same holdout used for candidate acceptance',
                        'independent forward test still required', 'not the production news/snapshot feature schema'],
    }


def decimal_argument(value: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("finite decimal required") from exc
    if not result.is_finite():
        raise argparse.ArgumentTypeError("finite decimal required")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--expected-trades', type=int, required=True)
    parser.add_argument('--expected-net-profit', type=decimal_argument, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        evidence = evaluate(args.journal, args.expected_trades, args.expected_net_profit)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(evidence['result'])
    print('reasons=' + ','.join(evidence['independent_audit']['reasons']))
    return 0 if evidence['result'] == 'PASS_RESEARCH_FINAL_AUDIT' else 2


if __name__ == '__main__':
    raise SystemExit(main())
