"""Deprecated location; use ``katarina.intelligence.perception.observational_associations``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import observational_associations as _module

warnings.warn("katarina.intelligence.observational_associations moved to katarina.intelligence.perception.observational_associations",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
