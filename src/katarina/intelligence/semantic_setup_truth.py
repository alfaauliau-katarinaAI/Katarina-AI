"""Deprecated location; use ``katarina.intelligence.perception.semantic_setup_truth``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import semantic_setup_truth as _module

warnings.warn("katarina.intelligence.semantic_setup_truth moved to katarina.intelligence.perception.semantic_setup_truth",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
