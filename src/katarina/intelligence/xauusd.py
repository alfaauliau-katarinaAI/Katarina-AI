"""Deprecated location; use ``katarina.intelligence.perception.xauusd``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import xauusd as _module

warnings.warn("katarina.intelligence.xauusd moved to katarina.intelligence.perception.xauusd",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
