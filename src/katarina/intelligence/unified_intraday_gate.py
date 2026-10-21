"""Deprecated location; use ``katarina.intelligence.lab.unified_intraday_gate``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import unified_intraday_gate as _module

warnings.warn("katarina.intelligence.unified_intraday_gate moved to katarina.intelligence.lab.unified_intraday_gate",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
