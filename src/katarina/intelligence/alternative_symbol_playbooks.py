"""Deprecated location; use ``katarina.intelligence.perception.alternative_symbol_playbooks``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import alternative_symbol_playbooks as _module

warnings.warn("katarina.intelligence.alternative_symbol_playbooks moved to katarina.intelligence.perception.alternative_symbol_playbooks",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
