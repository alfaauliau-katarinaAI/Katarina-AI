"""Deprecated location; use ``katarina.intelligence.demo.forward_outcomes``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.demo import forward_outcomes as _module

warnings.warn("katarina.intelligence.forward_outcomes moved to katarina.intelligence.demo.forward_outcomes",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
