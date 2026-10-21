"""Deprecated location; use ``katarina.intelligence.broker.broker_history_coverage``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.broker import broker_history_coverage as _module

warnings.warn("katarina.intelligence.broker_history_coverage moved to katarina.intelligence.broker.broker_history_coverage",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
