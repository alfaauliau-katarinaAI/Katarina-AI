"""Deprecated location; use ``katarina.intelligence.lab.closed_bar_failure_forensics``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import closed_bar_failure_forensics as _module

warnings.warn("katarina.intelligence.closed_bar_failure_forensics moved to katarina.intelligence.lab.closed_bar_failure_forensics",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
