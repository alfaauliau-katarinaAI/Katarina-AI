"""Deprecated location; use ``katarina.intelligence.news.public_context``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import public_context as _module

warnings.warn("katarina.intelligence.public_context moved to katarina.intelligence.news.public_context",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
