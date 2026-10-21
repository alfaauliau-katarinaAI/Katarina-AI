"""Deprecated location; use ``katarina.intelligence.shadow.shadow_research_evaluation``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import shadow_research_evaluation as _module

warnings.warn("katarina.intelligence.shadow_research_evaluation moved to katarina.intelligence.shadow.shadow_research_evaluation",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
