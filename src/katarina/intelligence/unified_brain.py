"""Deprecated location; use ``katarina.intelligence.cognition.unified_brain``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import unified_brain as _module

warnings.warn("katarina.intelligence.unified_brain moved to katarina.intelligence.cognition.unified_brain",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
