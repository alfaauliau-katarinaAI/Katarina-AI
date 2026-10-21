"""Deprecated location; use ``katarina.intelligence.cognition.unified_adaptive_research_cycle``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import unified_adaptive_research_cycle as _module

warnings.warn("katarina.intelligence.unified_adaptive_research_cycle moved to katarina.intelligence.cognition.unified_adaptive_research_cycle",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
