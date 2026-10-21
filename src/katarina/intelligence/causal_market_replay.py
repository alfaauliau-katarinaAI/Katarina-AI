"""Deprecated location; use ``katarina.intelligence.lab.causal_market_replay``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import causal_market_replay as _module

warnings.warn("katarina.intelligence.causal_market_replay moved to katarina.intelligence.lab.causal_market_replay",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
