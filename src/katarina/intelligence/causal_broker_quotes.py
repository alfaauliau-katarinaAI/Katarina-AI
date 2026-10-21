"""Deprecated location; use ``katarina.intelligence.broker.causal_broker_quotes``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.broker import causal_broker_quotes as _module

warnings.warn("katarina.intelligence.causal_broker_quotes moved to katarina.intelligence.broker.causal_broker_quotes",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
