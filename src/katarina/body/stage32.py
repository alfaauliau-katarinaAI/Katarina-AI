"""Deprecated alias kept for one release; use ``katarina.body.dashboard`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import dashboard as _module

warnings.warn("katarina.body.stage32 moved to katarina.body.dashboard", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
