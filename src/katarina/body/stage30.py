"""Deprecated alias kept for one release; use ``katarina.body.portfolio`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import portfolio as _module

warnings.warn("katarina.body.stage30 moved to katarina.body.portfolio", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
