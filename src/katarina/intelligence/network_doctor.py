"""Deprecated location; use ``katarina.intelligence.operations.network_doctor``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.operations import network_doctor as _module

warnings.warn("katarina.intelligence.network_doctor moved to katarina.intelligence.operations.network_doctor",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
