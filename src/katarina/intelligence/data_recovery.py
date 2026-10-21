"""Deprecated location; use ``katarina.intelligence.broker.data_recovery``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.broker import data_recovery as _module

warnings.warn("katarina.intelligence.data_recovery moved to katarina.intelligence.broker.data_recovery",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
