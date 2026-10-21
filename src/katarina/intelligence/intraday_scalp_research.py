"""Deprecated location; use ``katarina.intelligence.lab.intraday_scalp_research``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import intraday_scalp_research as _module

warnings.warn("katarina.intelligence.intraday_scalp_research moved to katarina.intelligence.lab.intraday_scalp_research",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
