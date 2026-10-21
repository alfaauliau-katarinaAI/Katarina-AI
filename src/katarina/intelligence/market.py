"""Deprecated location; use ``katarina.intelligence.perception.market``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import market as _module

warnings.warn("katarina.intelligence.market moved to katarina.intelligence.perception.market",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
