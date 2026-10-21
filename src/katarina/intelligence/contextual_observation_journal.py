"""Deprecated location; use ``katarina.intelligence.shadow.contextual_observation_journal``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import contextual_observation_journal as _module

warnings.warn("katarina.intelligence.contextual_observation_journal moved to katarina.intelligence.shadow.contextual_observation_journal",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
