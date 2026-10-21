"""Deprecated alias kept for one release; use ``katarina.body.stress_test`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import stress_test as _module

warnings.warn("katarina.body.stage37 moved to katarina.body.stress_test", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
