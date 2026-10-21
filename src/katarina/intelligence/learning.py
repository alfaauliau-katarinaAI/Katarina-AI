"""Deprecated location; use ``katarina.intelligence.perception.learning``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import learning as _module

warnings.warn("katarina.intelligence.learning moved to katarina.intelligence.perception.learning",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
