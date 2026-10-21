"""Deprecated location; use ``katarina.intelligence.cognition.observer``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import observer as _module

warnings.warn("katarina.intelligence.brain_observer moved to katarina.intelligence.cognition.observer",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
