"""Deprecated location; use ``katarina.intelligence.perception.cost_expectancy``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import cost_expectancy as _module

warnings.warn("katarina.intelligence.cost_expectancy moved to katarina.intelligence.perception.cost_expectancy",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
