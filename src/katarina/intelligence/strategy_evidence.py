"""Deprecated location; use ``katarina.intelligence.shadow.strategy_evidence``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import strategy_evidence as _module

warnings.warn("katarina.intelligence.strategy_evidence moved to katarina.intelligence.shadow.strategy_evidence",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
