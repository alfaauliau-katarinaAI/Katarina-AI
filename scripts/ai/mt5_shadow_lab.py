"""KATARINA MT5 shadow intraday laboratory — READ ONLY, no broker orders.

Example (outside market close, using a *dedicated* MT5 terminal/profile):
  python scripts/ai/mt5_shadow_lab.py \
    --terminal "C:\\Program Files\\MetaTrader 5 ALFA\\terminal64.exe" \
    --state-root "C:\\KatarinaShadowData" \
    --frozen-at 2026-10-11T00:00:00+00:00 \
    --version GOLD_SHADOW_20261011_V1 \
    --initial-paper-balance-native 1000 --cycles 1

Default is NO_TRADE if real-time news clearance has not been confirmed.
The research-only --ignore-news-for-paper flag skips this *paper* gate
but all such outcomes remain costs_verified=False and cannot pass the
forward promotion gate. Never run on real accounts for placing orders.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from math import isfinite
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))

from katarina.adapters.mt5_shadow_read_only import MT5ShadowReadOnly
from katarina.engines.risk import RiskGovernor
from katarina.intelligence.broker.mt5_shadow_cycle import MT5ShadowCycle
from katarina.intelligence.shadow.shadow_journal import ShadowJournal
from katarina.intelligence.shadow.shadow_paper_book import ShadowPaperBook
from katarina.intelligence.shadow.shadow_manifest import (
    ShadowStudyIdentity,broker_fingerprint,config_sha256,
    verify_or_create_manifest,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--terminal",type=Path,required=True,
                   help="Approved MT5 terminal64.exe path; initialization only")
    p.add_argument("--symbol",default="XAUUSD.vx")
    p.add_argument("--state-root",type=Path,required=True,
                   help="Private durable state directory, outside git checkout")
    p.add_argument("--risk-config",type=Path,
                   default=ROOT/"config"/"risk_governor_v2.json")
    p.add_argument("--frozen-at",required=True,
                   help="ISO8601 aware UTC/offset timestamp of setup freeze")
    p.add_argument("--version",required=True,
                   help="Immutable frozen strategy version (different after edits)")
    p.add_argument("--initial-paper-balance-native",type=float,required=True,
                   help="Virtual balance in MT5 account units; USC is cents")
    p.add_argument("--commission-per-lot",type=float,default=None,
                   help="Paper estimate, ALWAYS unverified broker fee evidence")
    p.add_argument("--ignore-news-for-paper",action="store_true",
                   help="Simulation only; never marks strategy evidence verified")
    p.add_argument("--cycles",type=int,default=1)
    p.add_argument("--poll-seconds",type=int,default=10)
    args=p.parse_args(argv)
    try:
        frozen=datetime.fromisoformat(args.frozen_at)
        if frozen.tzinfo is None or frozen.utcoffset() is None:
            raise ValueError("freeze timestamp must have explicit offset")
        if (args.cycles<1 or args.poll_seconds<5
                or not isfinite(args.initial_paper_balance_native)
                or args.initial_paper_balance_native<=0):
            raise ValueError("invalid cycles, poll interval or paper balance")
        if not args.symbol.startswith("XAUUSD"):
            raise ValueError("this frozen Gold shadow lab only supports XAUUSD")
        if args.state_root.resolve() == ROOT.resolve() or (
                ROOT.resolve() in args.state_root.resolve().parents):
            raise ValueError("do not write shadow state within git repository")
        if args.state_root.exists() and not args.state_root.is_dir():
            raise ValueError("shadow state root is not a directory")
        if args.commission_per_lot is not None and (
                not isfinite(args.commission_per_lot) or args.commission_per_lot<0):
            raise ValueError("invalid commission")
    except (ValueError,OverflowError) as exc:
        p.error(str(exc))
    return args


def main(argv: list[str] | None = None) -> int:
    args=parse_args(argv)
    # An O_EXCL lock rejects a second writer, including stale/crashed locks:
    # investigate and remove stale locks MANUALLY after verifying no process.
    args.state_root.mkdir(parents=True,exist_ok=True)
    lock_path=args.state_root/".shadow-single-writer.lock"
    try:
        fd=os.open(lock_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise RuntimeError("shadow_journal_writer_already_active_or_stale") from exc
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            f.write(str(os.getpid())+"\n")
            f.flush()
            os.fsync(f.fileno())
        try:
            import MetaTrader5 as mt5  # Only available on MT5-enabled VPS.
        except ImportError as exc:
            raise RuntimeError("MetaTrader5_dependency_required_on_vps_only") from exc
        if not mt5.initialize(path=str(args.terminal),timeout=15000):
            raise RuntimeError(f"MT5_readonly_connect_failed:{mt5.last_error()}")
        try:
            broker=MT5ShadowReadOnly(mt5)
            account=mt5.account_info()
            if account is None:
                raise RuntimeError("MT5_account_unavailable")
            policy=RiskGovernor.from_config(args.risk_config)
            verify_or_create_manifest(
                args.state_root,ShadowStudyIdentity(
                    strategy_version=args.version,
                    frozen_at_utc=datetime.fromisoformat(args.frozen_at)
                        .astimezone(timezone.utc).isoformat(),
                    symbol=args.symbol,account_currency=str(account.currency),
                    broker_account_fingerprint=broker_fingerprint(
                        server=str(account.server),login=account.login,
                        currency=str(account.currency)),
                    initial_paper_balance_native=args.initial_paper_balance_native,
                    risk_config_sha256=config_sha256(args.risk_config),
                    commission_per_lot_assumed=args.commission_per_lot,
                ))
            journal=ShadowJournal(args.state_root/"journal")
            paper=ShadowPaperBook(args.state_root/"paper",journal)
            controller=MT5ShadowCycle(
                broker=broker,journal=journal,paper_book=paper,
                risk_governor=policy,
                frozen_at_utc=datetime.fromisoformat(args.frozen_at),
                strategy_version=args.version,
                initial_paper_balance_account=args.initial_paper_balance_native,
                commission_round_trip_per_lot=args.commission_per_lot)
            for i in range(args.cycles):
                result=controller.run_once(
                    args.symbol,observed_at_utc=datetime.now(timezone.utc),
                    research_news_clear=args.ignore_news_for_paper)
                print(json.dumps({
                    **asdict(result),
                    "mode":"PAPER_READ_ONLY","broker_orders_sent":0,
                    "costs_verified":False,
                    "source":"live_observed_MT5_bid_ask",
                    "strategy_promoted":False},sort_keys=True),flush=True)
                if i+1<args.cycles:
                    time.sleep(args.poll_seconds)
        finally:
            mt5.shutdown()
    finally:
        lock_path.unlink(missing_ok=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
