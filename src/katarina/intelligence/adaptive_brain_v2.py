"""Deprecated location; use ``katarina.intelligence.cognition.adaptive_observation``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import adaptive_observation as _module

warnings.warn("katarina.intelligence.adaptive_brain_v2 moved to katarina.intelligence.cognition.adaptive_observation",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
