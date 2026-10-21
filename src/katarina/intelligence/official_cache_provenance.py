"""Deprecated location; use ``katarina.intelligence.news.official_cache_provenance``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import official_cache_provenance as _module

warnings.warn("katarina.intelligence.official_cache_provenance moved to katarina.intelligence.news.official_cache_provenance",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
