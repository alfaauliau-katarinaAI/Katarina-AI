"""Deprecated location; use ``katarina.intelligence.perception.symbol_playbooks``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import symbol_playbooks as _module

warnings.warn("katarina.intelligence.symbol_playbooks moved to katarina.intelligence.perception.symbol_playbooks",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
