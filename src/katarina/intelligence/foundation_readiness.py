"""Deprecated location; use ``katarina.intelligence.operations.foundation_readiness``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.operations import foundation_readiness as _module

warnings.warn("katarina.intelligence.foundation_readiness moved to katarina.intelligence.operations.foundation_readiness",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
