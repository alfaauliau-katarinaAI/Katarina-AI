"""Deprecated location; use ``katarina.intelligence.lab.precommitted_setup_research``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import precommitted_setup_research as _module

warnings.warn("katarina.intelligence.precommitted_setup_research moved to katarina.intelligence.lab.precommitted_setup_research",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
