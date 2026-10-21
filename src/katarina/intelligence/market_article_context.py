"""Deprecated location; use ``katarina.intelligence.news.market_article_context``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import market_article_context as _module

warnings.warn("katarina.intelligence.market_article_context moved to katarina.intelligence.news.market_article_context",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
