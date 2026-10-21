"""Deprecated location; use ``katarina.intelligence.cognition.owner_research_review``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import owner_research_review as _module

warnings.warn("katarina.intelligence.owner_research_review moved to katarina.intelligence.cognition.owner_research_review",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
