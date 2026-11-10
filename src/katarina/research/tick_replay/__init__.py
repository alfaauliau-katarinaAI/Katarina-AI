"""Offline tick-replay simulator for the six pre-registered XAUUSD candidates (D10-K1..K27).

Research only: no MT5 connection, no orders, no performance metrics. See
``docs/research/TICK_REPLAY_SIMULATOR.md`` for scope, inputs and the Owner gate before any real-data run.
"""
from .contract import (SIX_CANDIDATES, CandidateSpec, CostSpec, DatasetEvidence, ReplayInputError, SessionEvidence,
                       SymbolContract, Tick, validate_ticks)
from .engine import ENGINE_VERSION, TickReplay

__all__ = ["SIX_CANDIDATES", "CandidateSpec", "CostSpec", "DatasetEvidence", "ENGINE_VERSION", "ReplayInputError",
           "SessionEvidence", "SymbolContract", "Tick", "TickReplay", "validate_ticks"]
