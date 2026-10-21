"""Deprecated location; use ``katarina.intelligence.broker.broker_account_monitor``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.broker import broker_account_monitor as _module

warnings.warn("katarina.intelligence.broker_account_monitor moved to katarina.intelligence.broker.broker_account_monitor",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
