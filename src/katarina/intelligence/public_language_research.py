"""Deprecated location; use ``katarina.intelligence.news.public_language_research``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import public_language_research as _module

warnings.warn("katarina.intelligence.public_language_research moved to katarina.intelligence.news.public_language_research",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
