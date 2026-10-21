"""Deprecated location; use ``katarina.intelligence.perception.screening``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import screening as _module

warnings.warn("katarina.intelligence.multi_market_brain moved to katarina.intelligence.perception.screening",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
