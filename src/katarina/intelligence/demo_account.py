"""Deprecated location; use ``katarina.intelligence.demo.demo_account``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.demo import demo_account as _module

warnings.warn("katarina.intelligence.demo_account moved to katarina.intelligence.demo.demo_account",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
