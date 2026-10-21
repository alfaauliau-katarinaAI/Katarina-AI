"""Deprecated location; use ``katarina.intelligence.cognition.assistant_cycle``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import assistant_cycle as _module

warnings.warn("katarina.intelligence.assistant_cycle moved to katarina.intelligence.cognition.assistant_cycle",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
