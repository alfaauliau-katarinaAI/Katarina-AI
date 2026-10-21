"""Deprecated location; use ``katarina.intelligence.cognition.explainable_market_decision``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import explainable_market_decision as _module

warnings.warn("katarina.intelligence.explainable_market_decision moved to katarina.intelligence.cognition.explainable_market_decision",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
