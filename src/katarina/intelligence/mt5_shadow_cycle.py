"""Deprecated location; use ``katarina.intelligence.broker.mt5_shadow_cycle``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.broker import mt5_shadow_cycle as _module

warnings.warn("katarina.intelligence.mt5_shadow_cycle moved to katarina.intelligence.broker.mt5_shadow_cycle",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
