"""WP9b decision inputs: compare legacy and measured context, read-only.

Mode selection affects research-only contextual inputs; nothing here sends orders,
enables execution, or overrides the contextual risk gate.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path

from katarina.intelligence.news.news_intelligence import NewsContext

SCHEMA_VERSION = 1
LEGACY_MODE = "legacy_fail_closed"
MEASURED_MODE = "measured_inputs"
VALID_MODES = frozenset((LEGACY_MODE, MEASURED_MODE))


@dataclass(frozen=True)
class DecisionInputs:
    mode: str = LEGACY_MODE

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError("INVALID_DECISION_INPUTS_MODE")

    @property
    def shadow_mode(self) -> str:
        return MEASURED_MODE if self.mode == LEGACY_MODE else LEGACY_MODE

    def system_healthy(
        self, *, quote_fresh: bool, recent: bool, trade_mode: int,
        clock_verified: bool, previous_ledger_cycle: bool,
    ) -> bool:
        if self.mode == LEGACY_MODE:
            return False
        return bool(
            quote_fresh is True and recent is True
            and type(trade_mode) is int and trade_mode in (1, 2, 4)
            and clock_verified is True and previous_ledger_cycle is True
        )

    def news_context(self, news: NewsContext, calendar: dict) -> NewsContext:
        if self.mode == LEGACY_MODE:
            return news
        if (
            news.matched_items == 0
            and "no_fresh_relevant_news_context" in news.reasons
            and calendar.get("ready") is True
            and calendar.get("blackout") is False
        ):
            return replace(
                news, ready=False, blackout=False, risk_score=0.0,
                reasons=tuple(reason for reason in news.reasons
                              if reason != "no_fresh_relevant_news_context")
                        + ("no_fresh_relevant_news_calendar_clear",),
            )
        return news


def load_decision_inputs(path: str | Path | None) -> DecisionInputs:
    """No explicit config means legacy; malformed config must fail closed."""
    if path is None:
        return DecisionInputs()
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise ValueError("INVALID_DECISION_INPUTS_CONFIG") from exc
    if (
        type(config) is not dict
        or set(config) != {"schema_version", "mode"}
        or type(config["schema_version"]) is not int
        or config["schema_version"] != SCHEMA_VERSION
        or type(config["mode"]) is not str
        or config["mode"] not in VALID_MODES
    ):
        raise ValueError("INVALID_DECISION_INPUTS_CONFIG")
    return DecisionInputs(mode=config["mode"])
