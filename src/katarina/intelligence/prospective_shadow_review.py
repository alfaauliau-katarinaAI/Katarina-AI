"""Deprecated location; use ``katarina.intelligence.shadow.prospective_shadow_review``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import prospective_shadow_review as _module

warnings.warn("katarina.intelligence.prospective_shadow_review moved to katarina.intelligence.shadow.prospective_shadow_review",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
