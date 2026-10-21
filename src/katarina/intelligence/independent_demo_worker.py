"""Deprecated location; use ``katarina.intelligence.demo.independent_demo_worker``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.demo import independent_demo_worker as _module

warnings.warn("katarina.intelligence.independent_demo_worker moved to katarina.intelligence.demo.independent_demo_worker",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
