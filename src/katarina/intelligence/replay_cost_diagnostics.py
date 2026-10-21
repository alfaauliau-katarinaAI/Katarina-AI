"""Deprecated location; use ``katarina.intelligence.lab.replay_cost_diagnostics``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import replay_cost_diagnostics as _module

warnings.warn("katarina.intelligence.replay_cost_diagnostics moved to katarina.intelligence.lab.replay_cost_diagnostics",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
