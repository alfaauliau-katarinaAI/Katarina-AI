"""Deprecated location; use ``katarina.intelligence.perception.closed_swing_structure``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import closed_swing_structure as _module

warnings.warn("katarina.intelligence.closed_swing_structure moved to katarina.intelligence.perception.closed_swing_structure",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
