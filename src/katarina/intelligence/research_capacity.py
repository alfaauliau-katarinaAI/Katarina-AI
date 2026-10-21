"""Deprecated location; use ``katarina.intelligence.lab.research_capacity``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import research_capacity as _module

warnings.warn("katarina.intelligence.research_capacity moved to katarina.intelligence.lab.research_capacity",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
