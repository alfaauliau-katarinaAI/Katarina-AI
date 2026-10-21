"""Deprecated location; use ``katarina.intelligence.perception.structural_entry_quality``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import structural_entry_quality as _module

warnings.warn("katarina.intelligence.structural_entry_quality moved to katarina.intelligence.perception.structural_entry_quality",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
