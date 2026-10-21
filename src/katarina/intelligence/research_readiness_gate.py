"""Deprecated location; use ``katarina.intelligence.lab.research_readiness_gate``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import research_readiness_gate as _module

warnings.warn("katarina.intelligence.research_readiness_gate moved to katarina.intelligence.lab.research_readiness_gate",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
