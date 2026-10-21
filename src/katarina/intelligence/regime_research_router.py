"""Deprecated location; use ``katarina.intelligence.lab.regime_research_router``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import regime_research_router as _module

warnings.warn("katarina.intelligence.regime_research_router moved to katarina.intelligence.lab.regime_research_router",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
