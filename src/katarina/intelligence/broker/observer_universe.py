"""WP1 Stage-0 explicit broker universe; read-only, nothing here sends orders.

Canonical observer retains the old broker-driven default when no universe is
provided. A configured core symbol is NEVER replaced by an alias or cut by the
VPS host's three-symbol heuristic. The caller records missing core symbols.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

_VALID_SYMBOL = re.compile(r"^[A-Za-z0-9_.#-]{1,40}$")
_ALLOWED_TRADE_MODES = frozenset((1, 2, 4))
MAX_OBSERVER_SYMBOLS = 17


@dataclass(frozen=True)
class ObserverUniverse:
    core: tuple[str, ...]
    rotating_slots: int = 0

    def __post_init__(self):
        if (type(self.core) is not tuple or not self.core
                or any(type(s) is not str or not _VALID_SYMBOL.fullmatch(s)
                       for s in self.core)
                or len(set(self.core)) != len(self.core)):
            raise ValueError("INVALID_OBSERVER_CORE_SYMBOLS")
        if (type(self.rotating_slots) is not int
                or not 0 <= self.rotating_slots <= 10
                or len(self.core) + self.rotating_slots > MAX_OBSERVER_SYMBOLS):
            raise ValueError("INVALID_OBSERVER_ROTATING_SLOTS")


def load_universe(path) -> ObserverUniverse:
    """Load explicit broker symbol names; reject an unavailable/bad spec."""
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise ValueError("INVALID_OBSERVER_UNIVERSE_CONFIG") from exc
    if (not isinstance(spec, dict)
            or type(spec.get("schema_version")) is not int
            or spec["schema_version"] != 1
            or type(spec.get("core")) is not list):
        raise ValueError("INVALID_OBSERVER_UNIVERSE_CONFIG")
    return ObserverUniverse(tuple(spec["core"]),
                            spec.get("rotating_slots", 0))


def select_symbols(universe: ObserverUniverse, catalog, *,
                   rotation=None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (selected, missing_core) from exact enabled broker symbols.

    Rotating slots are opt-in; the rotation callback receives (budget,
    exclude_core_names). Unknown, disabled and repeated symbols are ignored.
    """
    if not isinstance(universe, ObserverUniverse):
        raise ValueError("INVALID_OBSERVER_UNIVERSE")
    if catalog is None:
        raise ValueError("BROKER_CATALOG_UNAVAILABLE")
    available = {
        s.name for s in catalog
        if isinstance(getattr(s, "name", None), str)
        and getattr(s, "trade_mode", 0) in _ALLOWED_TRADE_MODES
    }
    selected = [name for name in universe.core if name in available]
    missing = [name for name in universe.core if name not in available]
    if universe.rotating_slots and rotation is not None:
        proposed = rotation(universe.rotating_slots, universe.core)
        if not isinstance(proposed, (list, tuple)):
            raise ValueError("INVALID_OBSERVER_ROTATION")
        selected_rotating = 0
        for name in proposed:
            if (name in available and name not in universe.core
                    and name not in selected
                    and selected_rotating < universe.rotating_slots):
                selected.append(name)
                selected_rotating += 1
    return tuple(selected), tuple(missing)
