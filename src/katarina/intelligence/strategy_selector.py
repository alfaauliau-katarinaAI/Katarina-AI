"""Deprecated location; use ``katarina.intelligence.lab.strategy_selector``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import strategy_selector as _module

warnings.warn("katarina.intelligence.strategy_selector moved to katarina.intelligence.lab.strategy_selector",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
