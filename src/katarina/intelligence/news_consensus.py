"""Deprecated location; use ``katarina.intelligence.news.news_consensus``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import news_consensus as _module

warnings.warn("katarina.intelligence.news_consensus moved to katarina.intelligence.news.news_consensus",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
