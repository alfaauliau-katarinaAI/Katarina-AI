"""Deprecated location; use ``katarina.intelligence.lab.adaptive_walkforward``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import adaptive_walkforward as _module

warnings.warn("katarina.intelligence.adaptive_walkforward moved to katarina.intelligence.lab.adaptive_walkforward",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
