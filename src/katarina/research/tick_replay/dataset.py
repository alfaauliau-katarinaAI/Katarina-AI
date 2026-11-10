"""Load a broker tick file plus its evidence manifest for the tick-replay simulator, failing closed.

Expected inputs (research storage, never the Stage 0 ledger):

* a CSV exported from ``MetaTrader5.copy_ticks_range`` with at least the columns ``time_msc,bid,ask``
  (extra columns such as ``flags`` are ignored); row order is the source order;
* a JSON manifest with the keys ``dataset``, ``symbol_contract``, ``sessions`` and ``costs`` that describe
  the file's SHA-256, the broker symbol snapshot, the official sessions in UTC and the registered costs.

Nothing is repaired: an unknown hash, missing evidence, off-grid prices, crossed quotes, out-of-order rows or
rows after the development cutoff reject the whole input. Prices are converted to integer tick units.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from .contract import (CostSpec, DatasetEvidence, ReplayInputError, SessionEvidence, SymbolContract, Tick,
                       validate_ticks)

REQUIRED_COLUMNS = ("time_msc", "bid", "ask")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _spans(raw, name):
    try:
        return tuple((int(a), int(b)) for a, b in raw)
    except (TypeError, ValueError) as exc:
        raise ReplayInputError("SESSION_EVIDENCE_INVALID", f"{name}: {exc}") from exc


def load_manifest(path: Path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReplayInputError("MANIFEST_UNREADABLE", str(exc)) from exc
    for key in ("dataset", "symbol_contract", "costs"):
        if not isinstance(data.get(key), dict):
            raise ReplayInputError("MANIFEST_INCOMPLETE", key)
    try:
        dataset = DatasetEvidence(**data["dataset"])
        contract = SymbolContract(**data["symbol_contract"])
        costs = CostSpec(**data["costs"])
    except TypeError as exc:
        raise ReplayInputError("MANIFEST_INCOMPLETE", str(exc)) from exc
    sessions = None
    raw = data.get("sessions")
    if raw is not None:
        if not isinstance(raw, dict):
            raise ReplayInputError("SESSION_EVIDENCE_INVALID", "sessions must be an object")
        sessions = SessionEvidence(quote=_spans(raw.get("quote"), "quote"), trade=_spans(raw.get("trade"), "trade"),
                                   source=raw.get("source", ""), evidence_sha256=raw.get("evidence_sha256", ""))
    return dataset, contract, costs, sessions


def load_ticks(path: Path, contract: SymbolContract, dataset: DatasetEvidence):
    path = Path(path)
    actual = file_sha256(path)
    if actual != dataset.tick_file_sha256:
        raise ReplayInputError("TICK_FILE_HASH_MISMATCH", f"{actual} != {dataset.tick_file_sha256}")
    ticks = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ReplayInputError("TICK_FILE_COLUMNS_MISSING", ",".join(missing))
        for line, row in enumerate(reader, start=2):
            try:
                time_ms = int(row["time_msc"])
                bid, ask = float(row["bid"]), float(row["ask"])
            except (TypeError, ValueError) as exc:
                raise ReplayInputError("TICK_ROW_INVALID", f"line {line}: {exc}") from exc
            ticks.append(Tick(len(ticks), time_ms, contract.to_ticks(bid), contract.to_ticks(ask)))
    return validate_ticks(ticks, contract)


def load_inputs(tick_path: Path, manifest_path: Path):
    dataset, contract, costs, sessions = load_manifest(manifest_path)
    ticks = load_ticks(tick_path, contract, dataset)
    return ticks, dataset, contract, costs, sessions
