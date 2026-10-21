"""Deprecated location; use ``katarina.intelligence.lab.autonomous_research``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import autonomous_research as _module

warnings.warn("katarina.intelligence.autonomous_research moved to katarina.intelligence.lab.autonomous_research",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
