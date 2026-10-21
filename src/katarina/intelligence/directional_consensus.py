"""Deprecated location; use ``katarina.intelligence.perception.directional_consensus``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import directional_consensus as _module

warnings.warn("katarina.intelligence.directional_consensus moved to katarina.intelligence.perception.directional_consensus",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
