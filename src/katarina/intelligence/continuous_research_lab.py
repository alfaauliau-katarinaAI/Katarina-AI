"""Deprecated location; use ``katarina.intelligence.lab.continuous_research_lab``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import continuous_research_lab as _module

warnings.warn("katarina.intelligence.continuous_research_lab moved to katarina.intelligence.lab.continuous_research_lab",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
