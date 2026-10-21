"""Deprecated location; use ``katarina.intelligence.news.economic_feed``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import economic_feed as _module

warnings.warn("katarina.intelligence.economic_feed moved to katarina.intelligence.news.economic_feed",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
