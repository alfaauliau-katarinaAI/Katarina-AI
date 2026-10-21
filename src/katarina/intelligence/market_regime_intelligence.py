"""Deprecated location; use ``katarina.intelligence.perception.market_regime_intelligence``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import market_regime_intelligence as _module

warnings.warn("katarina.intelligence.market_regime_intelligence moved to katarina.intelligence.perception.market_regime_intelligence",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
