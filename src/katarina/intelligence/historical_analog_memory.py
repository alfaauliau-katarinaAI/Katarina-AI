"""Deprecated location; use ``katarina.intelligence.perception.historical_analog_memory``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import historical_analog_memory as _module

warnings.warn("katarina.intelligence.historical_analog_memory moved to katarina.intelligence.perception.historical_analog_memory",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
