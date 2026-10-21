"""Bounded, broker-adaptive research scanner universe.

Only symbols actually advertised and trade-enabled by the connected broker
are scanned. This is not a trading whitelist or evidence of profitability.
"""
from __future__ import annotations

from dataclasses import dataclass

MAJORS = (
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
)
CROSSES = (
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD",
)
OPTIONAL_MARKETS = ("XAUUSD", "BTCUSD", "OIL", "US30", "US100")
MAX_SCAN_SYMBOLS = len(MAJORS) + len(CROSSES) + len(OPTIONAL_MARKETS)

# In preference order. The broker's real symbol remains the scanner key;
# aliases here DO NOT imply identical contracts across brokers.
ALIASES = {
    "OIL": ("USOIL", "XTIUSD", "WTIUSD", "WTI", "USCRUDE",
            "UKOIL", "XBRUSD", "BRENT"),
    "US30": ("US30", "DJ30", "WS30", "DJIA"),
    "US100": ("US100", "NAS100", "USTEC", "NASDAQ100", "NQ100", "NDX100", "NASDAQ"),
}
_ACCOUNT_SUFFIXES = frozenset(("M", "C", "PRO", "RAW", "ECN", "CENT", "MICRO"))


@dataclass(frozen=True)
class BrokerScanSelection:
    instruments: tuple[object, ...]
    matches: dict[str, str]
    unavailable: tuple[str, ...]

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(x.name for x in self.instruments)


def _match_quality(broker_name: str, alias: str) -> int | None:
    """Accept exact names or familiar broker suffixes, not unrelated tokens."""
    if broker_name == alias:
        return 0
    if not broker_name.startswith(alias):
        return None
    suffix = broker_name[len(alias):]
    if suffix in _ACCOUNT_SUFFIXES:
        return 2
    if (len(suffix) >= 2 and suffix[0] in "._-#"
            and all(c.isalnum() or c in "._-" for c in suffix[1:])):
        return 1
    return None


def resolve_broker_symbols(catalog) -> BrokerScanSelection:
    """Pick at most one eligible broker instrument per requested market.

    Missing, disabled or differently named symbols are nonfatal; no synthetic
    symbol is ever passed to MT5. An unavailable catalog is a caller error
    (the caller must fail closed rather than treat it as zero instruments).
    """
    if catalog is None:
        raise ValueError("broker_catalog_unavailable")
    available = [
        s for s in catalog
        if isinstance(getattr(s, "name", None), str)
        and getattr(s, "trade_mode", 0) in (1, 2, 4)
    ]
    picked: list[object] = []
    matches: dict[str, str] = {}
    missing: list[str] = []
    used: set[str] = set()
    for canonical in (*MAJORS, *CROSSES, *OPTIONAL_MARKETS):
        aliases = ALIASES.get(canonical, (canonical,))
        options = []
        for symbol in available:
            raw = symbol.name.upper()
            if raw in used:
                continue
            for index, alias in enumerate(aliases):
                quality = _match_quality(raw, alias)
                if quality is not None:
                    options.append(((index, quality, len(raw), raw), symbol))
                    break
        if options:
            symbol = min(options, key=lambda x: x[0])[1]
            picked.append(symbol)
            matches[canonical] = symbol.name
            used.add(symbol.name.upper())
        else:
            missing.append(canonical)
    return BrokerScanSelection(tuple(picked), matches, tuple(missing))
