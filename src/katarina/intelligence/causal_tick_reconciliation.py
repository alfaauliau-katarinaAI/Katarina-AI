"""Deprecated location; use ``katarina.intelligence.lab.causal_tick_reconciliation``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import causal_tick_reconciliation as _module

warnings.warn("katarina.intelligence.causal_tick_reconciliation moved to katarina.intelligence.lab.causal_tick_reconciliation",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
