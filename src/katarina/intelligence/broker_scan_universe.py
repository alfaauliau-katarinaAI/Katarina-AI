"""Deprecated location; use ``katarina.intelligence.broker.broker_scan_universe``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.broker import broker_scan_universe as _module

warnings.warn("katarina.intelligence.broker_scan_universe moved to katarina.intelligence.broker.broker_scan_universe",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
