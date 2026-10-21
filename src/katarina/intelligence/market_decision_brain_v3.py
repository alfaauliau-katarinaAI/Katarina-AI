"""Deprecated location; use ``katarina.intelligence.cognition.market_decision``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import market_decision as _module

warnings.warn("katarina.intelligence.market_decision_brain_v3 moved to katarina.intelligence.cognition.market_decision",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
