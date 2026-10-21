"""Deprecated location; use ``katarina.intelligence.lab.offline_hand_telemetry``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import offline_hand_telemetry as _module

warnings.warn("katarina.intelligence.offline_hand_telemetry moved to katarina.intelligence.lab.offline_hand_telemetry",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
