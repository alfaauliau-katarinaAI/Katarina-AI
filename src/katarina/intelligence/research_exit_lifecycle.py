"""Deprecated location; use ``katarina.intelligence.lab.research_exit_lifecycle``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import research_exit_lifecycle as _module

warnings.warn("katarina.intelligence.research_exit_lifecycle moved to katarina.intelligence.lab.research_exit_lifecycle",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
