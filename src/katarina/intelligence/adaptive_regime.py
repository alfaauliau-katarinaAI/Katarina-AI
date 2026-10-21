"""Deprecated location; use ``katarina.intelligence.perception.adaptive_regime``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import adaptive_regime as _module

warnings.warn("katarina.intelligence.adaptive_regime moved to katarina.intelligence.perception.adaptive_regime",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
