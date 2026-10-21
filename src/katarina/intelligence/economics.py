"""Deprecated location; use ``katarina.intelligence.perception.economics``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import economics as _module

warnings.warn("katarina.intelligence.economics moved to katarina.intelligence.perception.economics",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
