"""Deprecated location; use ``katarina.intelligence.perception.simple_ml``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import simple_ml as _module

warnings.warn("katarina.intelligence.simple_ml moved to katarina.intelligence.perception.simple_ml",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
