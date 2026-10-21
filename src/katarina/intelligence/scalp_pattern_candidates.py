"""Deprecated location; use ``katarina.intelligence.perception.scalp_pattern_candidates``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import scalp_pattern_candidates as _module

warnings.warn("katarina.intelligence.scalp_pattern_candidates moved to katarina.intelligence.perception.scalp_pattern_candidates",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
