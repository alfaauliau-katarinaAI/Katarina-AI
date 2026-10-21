"""Deprecated location; use ``katarina.intelligence.lab.adaptive_strategy_library``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import adaptive_strategy_library as _module

warnings.warn("katarina.intelligence.adaptive_strategy_library moved to katarina.intelligence.lab.adaptive_strategy_library",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
