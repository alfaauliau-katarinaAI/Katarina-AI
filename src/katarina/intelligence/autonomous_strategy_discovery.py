"""Deprecated location; use ``katarina.intelligence.lab.autonomous_strategy_discovery``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import autonomous_strategy_discovery as _module

warnings.warn("katarina.intelligence.autonomous_strategy_discovery moved to katarina.intelligence.lab.autonomous_strategy_discovery",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
