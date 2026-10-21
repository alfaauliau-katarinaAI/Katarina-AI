"""Deprecated location; use ``katarina.intelligence.news.research_agenda``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import research_agenda as _module

warnings.warn("katarina.intelligence.research_agenda moved to katarina.intelligence.news.research_agenda",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
