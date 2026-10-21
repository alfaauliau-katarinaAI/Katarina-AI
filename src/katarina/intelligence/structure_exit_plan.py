"""Deprecated location; use ``katarina.intelligence.perception.structure_exit_plan``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import structure_exit_plan as _module

warnings.warn("katarina.intelligence.structure_exit_plan moved to katarina.intelligence.perception.structure_exit_plan",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
