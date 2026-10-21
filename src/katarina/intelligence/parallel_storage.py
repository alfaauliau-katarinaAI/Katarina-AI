"""Deprecated location; use ``katarina.intelligence.operations.parallel_storage``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.operations import parallel_storage as _module

warnings.warn("katarina.intelligence.parallel_storage moved to katarina.intelligence.operations.parallel_storage",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
