"""Deprecated location; use ``katarina.intelligence.demo.demo_forward``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.demo import demo_forward as _module

warnings.warn("katarina.intelligence.demo_forward moved to katarina.intelligence.demo.demo_forward",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
