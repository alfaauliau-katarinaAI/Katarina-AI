"""Deprecated location; use ``katarina.intelligence.perception.causal_seasonality``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import causal_seasonality as _module

warnings.warn("katarina.intelligence.causal_seasonality moved to katarina.intelligence.perception.causal_seasonality",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
