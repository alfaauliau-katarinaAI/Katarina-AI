"""Deprecated location; use ``katarina.intelligence.cognition.unified_research_handoff``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import unified_research_handoff as _module

warnings.warn("katarina.intelligence.unified_research_handoff moved to katarina.intelligence.cognition.unified_research_handoff",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
