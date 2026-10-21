"""Deprecated location; use ``katarina.intelligence.perception.timeframe``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import timeframe as _module

warnings.warn("katarina.intelligence.timeframe moved to katarina.intelligence.perception.timeframe",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
