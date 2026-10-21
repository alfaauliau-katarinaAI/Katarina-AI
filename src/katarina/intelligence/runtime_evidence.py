"""Deprecated location; use ``katarina.intelligence.operations.runtime_evidence``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.operations import runtime_evidence as _module

warnings.warn("katarina.intelligence.runtime_evidence moved to katarina.intelligence.operations.runtime_evidence",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
