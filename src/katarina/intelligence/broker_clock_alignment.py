"""Deprecated location; use ``katarina.intelligence.broker.broker_clock_alignment``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.broker import broker_clock_alignment as _module

warnings.warn("katarina.intelligence.broker_clock_alignment moved to katarina.intelligence.broker.broker_clock_alignment",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
