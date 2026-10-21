"""Deprecated location; use ``katarina.intelligence.shadow.shadow_journal``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import shadow_journal as _module

warnings.warn("katarina.intelligence.shadow_journal moved to katarina.intelligence.shadow.shadow_journal",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
