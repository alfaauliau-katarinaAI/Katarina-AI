"""Deprecated location; use ``katarina.intelligence.news.research_news_collection``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import research_news_collection as _module

warnings.warn("katarina.intelligence.research_news_collection moved to katarina.intelligence.news.research_news_collection",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
