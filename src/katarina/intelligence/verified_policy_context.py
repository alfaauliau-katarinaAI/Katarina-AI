"""Deprecated location; use ``katarina.intelligence.news.verified_policy_context``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.news import verified_policy_context as _module

warnings.warn("katarina.intelligence.verified_policy_context moved to katarina.intelligence.news.verified_policy_context",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
