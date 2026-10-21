"""Deprecated location; use ``katarina.intelligence.broker.auto_calibration``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.broker import auto_calibration as _module

warnings.warn("katarina.intelligence.auto_calibration moved to katarina.intelligence.broker.auto_calibration",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
