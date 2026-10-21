"""Deprecated location; use ``katarina.intelligence.operations.file_housekeeping``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.operations import file_housekeeping as _module

warnings.warn("katarina.intelligence.file_housekeeping moved to katarina.intelligence.operations.file_housekeeping",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
