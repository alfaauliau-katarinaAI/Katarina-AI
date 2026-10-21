"""Deprecated location; use ``katarina.intelligence.lab.research_reports``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import research_reports as _module

warnings.warn("katarina.intelligence.research_reports moved to katarina.intelligence.lab.research_reports",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
