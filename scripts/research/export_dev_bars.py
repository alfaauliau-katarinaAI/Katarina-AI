"""WP8a Tahap 1–2: export development-only broker bars; read-only, no orders.

Manual weekend-only use by Claude, outside the active 60-second observer:
  python scripts/research/export_dev_bars.py --out D:\\dev-dataset --start 2024-01-01

Requires an already installed MetaTrader5 package and authorized read-only
broker connection on the operator's own machine. Never touches holdout data.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from katarina.intelligence.broker.observer_universe import load_universe  # noqa: E402
from katarina.research.dev_dataset import export_dev_bars  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", default="config/observer_universe.json")
    parser.add_argument("--start", default="2024-01-01", help="Development start UTC date, YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="New frozen output directory (never observer state)")
    parser.add_argument("--chunk-days", type=int, default=7, help="Broker history batch size, 1..7 days")
    args = parser.parse_args(argv)
    start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    universe = load_universe(args.universe)
    if len(universe.core) != 7 or universe.rotating_slots:
        parser.error("WP8A_REQUIRES_EXACT_SEVEN_CORE_SYMBOLS")
    # Broker dependency is imported only when a human explicitly executes the CLI.
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("BROKER_INITIALIZE_FAILED")
    try:
        manifest = export_dev_bars(mt5, universe.core, start=start,
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
