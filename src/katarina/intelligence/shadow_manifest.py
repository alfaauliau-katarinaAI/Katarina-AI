"""Deprecated location; use ``katarina.intelligence.shadow.shadow_manifest``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import shadow_manifest as _module

warnings.warn("katarina.intelligence.shadow_manifest moved to katarina.intelligence.shadow.shadow_manifest",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
