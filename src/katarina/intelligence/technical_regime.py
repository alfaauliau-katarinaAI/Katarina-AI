"""Deprecated location; use ``katarina.intelligence.perception.technical_regime``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import technical_regime as _module

warnings.warn("katarina.intelligence.technical_regime moved to katarina.intelligence.perception.technical_regime",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
