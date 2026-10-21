"""Deprecated location; use ``katarina.intelligence.news.news_intelligence``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import news_intelligence as _module

warnings.warn("katarina.intelligence.news_intelligence moved to katarina.intelligence.news.news_intelligence",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
