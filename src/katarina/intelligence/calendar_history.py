"""Deprecated location; use ``katarina.intelligence.perception.calendar_history``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import calendar_history as _module

warnings.warn("katarina.intelligence.calendar_history moved to katarina.intelligence.perception.calendar_history",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
