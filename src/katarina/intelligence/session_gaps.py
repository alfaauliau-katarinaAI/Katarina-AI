"""Deprecated location; use ``katarina.intelligence.perception.session_gaps``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import session_gaps as _module

warnings.warn("katarina.intelligence.session_gaps moved to katarina.intelligence.perception.session_gaps",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
