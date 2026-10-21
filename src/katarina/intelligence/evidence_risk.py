"""Deprecated location; use ``katarina.intelligence.lab.evidence_risk``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import evidence_risk as _module

warnings.warn("katarina.intelligence.evidence_risk moved to katarina.intelligence.lab.evidence_risk",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
