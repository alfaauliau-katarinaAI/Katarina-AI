"""Deprecated location; use ``katarina.intelligence.cognition.self_evolution_lab``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import self_evolution_lab as _module

warnings.warn("katarina.intelligence.self_evolution_lab moved to katarina.intelligence.cognition.self_evolution_lab",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
