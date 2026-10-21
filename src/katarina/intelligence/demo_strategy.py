"""Deprecated location; use ``katarina.intelligence.demo.demo_strategy``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.demo import demo_strategy as _module

warnings.warn("katarina.intelligence.demo_strategy moved to katarina.intelligence.demo.demo_strategy",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
