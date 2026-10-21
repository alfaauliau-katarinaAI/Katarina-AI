"""Deprecated location; use ``katarina.intelligence.perception.analog_feature_schema``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.perception import analog_feature_schema as _module

warnings.warn("katarina.intelligence.analog_feature_schema moved to katarina.intelligence.perception.analog_feature_schema",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
