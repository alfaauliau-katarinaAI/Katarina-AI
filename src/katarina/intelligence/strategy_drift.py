"""Deprecated location; use ``katarina.intelligence.shadow.strategy_drift``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import strategy_drift as _module

warnings.warn("katarina.intelligence.strategy_drift moved to katarina.intelligence.shadow.strategy_drift",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
