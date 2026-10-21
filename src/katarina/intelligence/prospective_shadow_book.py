"""Deprecated location; use ``katarina.intelligence.shadow.prospective_shadow_book``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import prospective_shadow_book as _module

warnings.warn("katarina.intelligence.prospective_shadow_book moved to katarina.intelligence.shadow.prospective_shadow_book",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
