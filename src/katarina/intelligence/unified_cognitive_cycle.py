"""Deprecated location; use ``katarina.intelligence.cognition.unified_cognitive_cycle``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import unified_cognitive_cycle as _module

warnings.warn("katarina.intelligence.unified_cognitive_cycle moved to katarina.intelligence.cognition.unified_cognitive_cycle",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
