"""WP8a Tahap 1–2: export development-only broker bars; read-only, no orders.

Run ONLY on a separately approved Windows research machine with portable MT5,
AutoTrading OFF, no EAs and no observer. Before running, operator must put a
.katarina-research-terminal file containing ISOLATED_RESEARCH_ONLY in the
research terminal64.exe directory. Explicit --terminal-path and previously
verified --clock-evidence are mandatory. Never use the production VPS.

Requires an already installed MetaTrader5 package and authorized read-only
broker connection on the operator's own machine. Never touches holdout data.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from katarina.intelligence.broker.observer_universe import load_universe  # noqa: E402
from katarina.research.bar_clock_evidence import BarClockEvidenceAdapter, load_evidence_report  # noqa: E402
from katarina.research.dev_dataset import export_dev_bars  # noqa: E402
from scripts.research.build_bar_clock_evidence import initialize_research_terminal, is_path_inside_repo  # noqa: E402
from katarina.research.validation import ValidationError  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", default="config/observer_universe.json")
    parser.add_argument("--start", default="2024-01-01", help="Development start UTC date, YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="New frozen output directory (never observer state)")
    parser.add_argument("--chunk-days", type=int, default=7, help="Broker history batch size, 1..7 days")
    parser.add_argument("--clock-evidence", required=True, help="Verified historical clock evidence JSON (mandatory)")
    parser.add_argument("--terminal-path", required=True, help="Absolute terminal64.exe from SEPARATE, marked portable research MT5")
    args = parser.parse_args(argv)
    start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    universe = load_universe(args.universe)
    if len(universe.core) != 7 or universe.rotating_slots:
        parser.error("WP8A_REQUIRES_EXACT_SEVEN_CORE_SYMBOLS")
    if is_path_inside_repo(args.out):
        raise ValidationError("DATASET_OUTPUT_MUST_BE_OUTSIDE_REPO")
    if not Path(args.clock_evidence).is_file():
        raise ValidationError("CLOCK_EVIDENCE_NOT_FOUND")
    # Verify clock evidence BEFORE any possible MT5 process initialization.
    report = load_evidence_report(args.clock_evidence)
    # Broker dependency imported only after explicit operator path and evidence checks.
    import MetaTrader5 as mt5
    initialize_research_terminal(mt5, args.terminal_path)
    try:
        broker_target = BarClockEvidenceAdapter(mt5, report)
        manifest = export_dev_bars(broker_target, universe.core, start=start,
                                   out=args.out, chunk_days=args.chunk_days)
    finally:
        mt5.shutdown()
    print(json.dumps({"status": "FROZEN_DEVELOPMENT_ONLY",
                      "manifest_sha256": manifest["manifest_sha256"],
                      "symbols": manifest["symbols"],
                      "files": len(manifest["files"]),
                      "live_execution_authorized": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
