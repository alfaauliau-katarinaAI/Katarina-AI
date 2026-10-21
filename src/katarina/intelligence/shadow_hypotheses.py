"""Deprecated location; use ``katarina.intelligence.shadow.shadow_hypotheses``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import shadow_hypotheses as _module

warnings.warn("katarina.intelligence.shadow_hypotheses moved to katarina.intelligence.shadow.shadow_hypotheses",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
