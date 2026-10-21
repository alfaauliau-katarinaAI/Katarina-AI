"""Deprecated location; use ``katarina.intelligence.perception.multi_pair_arbitrator``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import multi_pair_arbitrator as _module

warnings.warn("katarina.intelligence.multi_pair_arbitrator moved to katarina.intelligence.perception.multi_pair_arbitrator",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
