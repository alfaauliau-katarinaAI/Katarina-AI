"""Deprecated location; use ``katarina.intelligence.perception.market_universe``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import market_universe as _module

warnings.warn("katarina.intelligence.market_universe moved to katarina.intelligence.perception.market_universe",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
