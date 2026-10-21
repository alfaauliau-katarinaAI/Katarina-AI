"""Deprecated location; use ``katarina.intelligence.cognition.continuous_observation``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import continuous_observation as _module

warnings.warn("katarina.intelligence.continuous_observation moved to katarina.intelligence.cognition.continuous_observation",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
