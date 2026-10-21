"""Deprecated location; use ``katarina.intelligence.cognition.contextual_decision_intelligence``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.cognition import contextual_decision_intelligence as _module

warnings.warn("katarina.intelligence.contextual_decision_intelligence moved to katarina.intelligence.cognition.contextual_decision_intelligence",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
