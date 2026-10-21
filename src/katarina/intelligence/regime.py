"""Deprecated location; use ``katarina.intelligence.perception.regime``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import regime as _module

warnings.warn("katarina.intelligence.regime moved to katarina.intelligence.perception.regime",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
