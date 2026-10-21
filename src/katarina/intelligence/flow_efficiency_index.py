"""Deprecated location; use ``katarina.intelligence.perception.flow_efficiency_index``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import flow_efficiency_index as _module

warnings.warn("katarina.intelligence.flow_efficiency_index moved to katarina.intelligence.perception.flow_efficiency_index",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
