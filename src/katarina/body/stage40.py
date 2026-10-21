"""Deprecated alias kept for one release; use ``katarina.body.continuous_evolution`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import continuous_evolution as _module

warnings.warn("katarina.body.stage40 moved to katarina.body.continuous_evolution", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
