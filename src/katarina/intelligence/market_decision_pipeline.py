"""Deprecated location; use ``katarina.intelligence.cognition.market_decision_pipeline``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import market_decision_pipeline as _module

warnings.warn("katarina.intelligence.market_decision_pipeline moved to katarina.intelligence.cognition.market_decision_pipeline",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
