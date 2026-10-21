"""Deprecated location; use ``katarina.intelligence.cognition.brain_runtime_control``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import brain_runtime_control as _module

warnings.warn("katarina.intelligence.brain_runtime_control moved to katarina.intelligence.cognition.brain_runtime_control",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
